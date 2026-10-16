# Station 066 · Social feed with keyset pagination

Working Systems · 0–2 years · Core · Social · Types: Database

Spring Boot 4.1.1 · Java 25 · JdbcClient · keyset (seek) pagination · row-value comparison · opaque cursors · PostgreSQL 17 · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Authors and posts are generated demo data (100,000 posts), not Chaupal's. There is no login; the feed is one public feed.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 11 tests.

# 1 · Understand

## The problem in real life

1.  **Scrolling the feed**

    A Chaupal user scrolls for a long time. Each new page is "skip N posts, show 20".

2.  **Slower and repeating**

    Page 2,000 has to read and discard 40,000 posts first: four seconds. And when friends post while the user reads page 1, every post moves down: the bottom of page 1 shows up again at the top of page 2.

3.  **The fix**

    Each page says where it stopped: the last post's time and id. The next page asks for posts older than that one, which the index finds directly, whatever was posted in between.

Page by position in the data, not by counting rows.

## What are we building?

`GET /feed` returns the newest posts and a `nextCursor`; `GET /feed?cursor=…` continues from there, at the same speed on page 2 and page 2,000.

## An everyday analogy

Reading a long newspaper archive. Offset paging is "start from the first issue and count 40,000 pages". Keyset paging is a bookmark: "the issue after 1 October, 05:33", and you open it there.

## How it works in 4 steps

1.  **First page**: the newest posts, one more than asked.
2.  **If there is that extra post**, there is a next page: the cursor is the last shown post's time and id.
3.  **Next page**: posts older than the cursor's post, in the same order, straight from the index.
4.  **The end**: fewer posts than asked, and no cursor.

Check yourself: why does the cursor need the id, and not just the time?

Five posts can share one second. If page 1 ends at the second of those five, "older than this time" skips the other four. "Older than (this time, this id)" continues with them. The test shows the four lost posts.

## What this station is not

- **No personal feed.** One public feed; following people is a filter (Practice 1).
- **No ranking.** Newest first only.
- **No page numbers.** Keyset paging cannot jump to page 517, by design.

## Key terms

| Term                     | Simple meaning                                     | Everyday example                                           | In this project                          |
|--------------------------|----------------------------------------------------|------------------------------------------------------------|------------------------------------------|
| **Offset paging**        | "Skip the first N, give me the next 20."           | Counting 40,000 envelopes to reach the 40,001st.           | the old feed: `OFFSET`                   |
| **Keyset (seek) paging** | "Give me the 20 that come after this one."         | A bookmark: open the book where you stopped.               | `WHERE (created_at, id) < (…)`           |
| **Cursor**               | A token saying where the last page stopped.        | The bookmark itself.                                       | `nextCursor`                             |
| **Opaque**               | Clients pass it back unchanged and do not read it. | A cloakroom token: you hand it back, you do not decode it. | base64url of `v1:1790832799000000:99998` |
| **Tie-breaking**         | A second key for rows with the same first key.     | Two posts in the same second, told apart by id.            | `id` after `created_at`                  |
| **Row-value comparison** | Comparing several columns at once, in order.       | Compare dates; if equal, compare numbers.                  | `(created_at, id) < (:t, :id)`           |

# 2 · Build: Spec

## Business problem

**Chaupal** (a fictional social app) pages its feed with `OFFSET`. Page 2,000 takes 4 seconds, and new posts push duplicates onto the next page.

## Acceptance criteria

Demo data: 100,000 posts, five per second, from 1 October 2026 00:00 UTC.

1.  **Given** no cursor, **then** posts 100000 down to 99981 and a `nextCursor`.
2.  **Given** that cursor, **then** the next posts with no gap and no repeat, even if posts were added meanwhile.
3.  **Given** a page boundary inside one second, **then** the posts sharing that second still appear.
4.  **Given** the last page, **then** `nextCursor` is `null`; a cursor past the oldest post gives an empty page.
5.  **Given** a cursor this feed did not make, or a limit outside 1 to 50, **then** `400`.
6.  **Given** page 2,000, **then** the database reads about one page of rows, not 40,000.

## Requirements

- Order by `(created_at, id)`, both descending, everywhere.
- The cursor holds both values; it is opaque and versioned.
- No count query: one extra row tells whether more follow.
- An index matches the order.

## Learning objectives

- Measure what `OFFSET` costs.
- Write a keyset page with a row-value comparison.
- Design an opaque cursor with a tie-breaker.
- Know what keyset paging cannot do.

# 2 · Build: API contract

## Endpoint

| Method | Path                      | Purpose                                                                   |
|--------|---------------------------|---------------------------------------------------------------------------|
| `GET`  | `/feed?limit=20`          | The newest posts: `{posts: [{id, author, body, createdAt}], nextCursor}`. |
| `GET`  | `/feed?cursor=…&limit=20` | The posts after the cursor; `nextCursor` is `null` at the end.            |

## Status codes

| Status | When                                                      |
|--------|-----------------------------------------------------------|
| 200    | A page, possibly empty                                    |
| 400    | A cursor this feed did not issue; a limit outside 1 to 50 |

## Captured examples

Captured with curl from the running app on 16 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: the newest three

**Why:** the first page and its cursor.

Request

``` code
GET /feed?limit=3 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 349

{
  "posts": [
    {
      "id": 100000,
      "author": "asha_writes",
      "body": "Post number 100000",
      "createdAt": "2026-10-01T05:33:20Z"
    },
    {
      "id": 99999,
      "author": "ravi_07",
      "body": "Post number 99999",
      "createdAt": "2026-10-01T05:33:19Z"
    },
    {
      "id": 99998,
      "author": "meera_k",
      "body": "Post number 99998",
      "createdAt": "2026-10-01T05:33:19Z"
    }
  ],
  "nextCursor": "djE6MTc5MDgzMjc5OTAwMDAwMDo5OTk5OA"
}
```

### Case 2: the cursor from case 1

**Why:** straight on, with the id deciding inside a second.

Request

``` code
GET /feed?limit=3&cursor=djE6MTc5MDgzMjc5OTAwMDAwMDo5OTk5OA HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 345

{
  "posts": [
    {
      "id": 99997,
      "author": "kabir",
      "body": "Post number 99997",
      "createdAt": "2026-10-01T05:33:19Z"
    },
    {
      "id": 99996,
      "author": "asha_writes",
      "body": "Post number 99996",
      "createdAt": "2026-10-01T05:33:19Z"
    },
    {
      "id": 99995,
      "author": "ravi_07",
      "body": "Post number 99995",
      "createdAt": "2026-10-01T05:33:19Z"
    }
  ],
  "nextCursor": "djE6MTc5MDgzMjc5OTAwMDAwMDo5OTk5NQ"
}
```

### Case 3: a made-up cursor

**Why:** `400`, telling the client to start again.

Request

``` code
GET /feed?cursor=bm90LW91cnM HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Not a cursor from this feed; start again without one",
  "instance": "/feed",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 4: limit 500

**Why:** `400`; at most 50.

Request

``` code
GET /feed?limit=500 HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Validation failure",
  "instance": "/feed",
  "status": 400,
  "title": "Bad Request"
}
```

The cursor in case 1 decodes to `v1:1790832799000000:99998`: version, the post's time in microseconds since 1970, and its id. Clients must not build or change it; the version lets the server change its contents later.

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                       | What happens                         | Proved by                                                     |
|--------------------------------------------|--------------------------------------|---------------------------------------------------------------|
| The first page                             | The newest 20 and a cursor           | `theFirstPageIsTheNewestPosts`                                |
| A boundary inside one second               | The id continues the order           | `theCursorContinuesExactlyWhereThePageStopped`                |
| Nineteen pages in a row; the last page     | Each post once; no cursor at the end | `walkingTheLastThousandPostsShowsEachOnceAndEndsWithNoCursor` |
| A cursor past the oldest post              | Empty page                           | `aCursorPastTheOldestPostIsAnEmptyPage`                       |
| A foreign or old-style cursor; a bad limit | `400`                                | `aCursorThatIsNotOursOrABadLimitIs400`                        |
| Posts added while reading                  | Offset repeats; keyset does not      | `newPostsPushRepeatsOntoTheNextOffsetPage`                    |
| Bad rows; a half-added author              | Refused; rolled back                 | `PostDatabaseTest`                                            |

## The trap

Plausible but wrong

Deep `OFFSET` paging that gets slower page by page and duplicates new posts.

- **Slower.** `OFFSET 40000` means reading 40,000 rows in order and throwing them away. In the captured plans, the scans produced 40,020 rows for the offset page and 21 for the keyset page (including the one-row lookup of the cursor's post).
- **Repeats.** Three new posts move everything down by three. Page 2 by offset starts with the last three posts of page 1; the keyset page starts after the last post the reader saw.
- **The first cursor people write.** "Older than this time" skips the posts that share the last post's second. Here, four of them.

While building, each fix was undone once: dropping the id from the cursor turned 4 tests red; not fetching the extra row 5; accepting any decoded text as a cursor 1; dropping the index 1.

``` code
                                      QUERY PLAN                                      
--------------------------------------------------------------------------------------
 Limit (actual rows=20 loops=1)
   Buffers: shared hit=531
   ->  Index Only Scan Backward using posts_feed on posts (actual rows=40020 loops=1)
         Heap Fetches: 40020
         Buffers: shared hit=531
 Planning:
   Buffers: shared hit=96
(7 rows)
```

``` code
                                    QUERY PLAN                                     
-----------------------------------------------------------------------------------
 Limit (actual rows=20 loops=1)
   Buffers: shared hit=6
   InitPlan 1
     ->  Index Scan using posts_pkey on posts posts_1 (actual rows=1 loops=1)
           Index Cond: (id = 60001)
           Buffers: shared hit=3
   ->  Index Only Scan Backward using posts_feed on posts (actual rows=20 loops=1)
         Index Cond: (ROW(created_at, id) < ROW((InitPlan 1).col1, 60001))
         Heap Fetches: 20
         Buffers: shared hit=6
 Planning:
   Buffers: shared hit=100
(12 rows)
```

``` code
package com.chaupal.feed;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/** Written first. The old OFFSET feed and a time-only cursor, against the keyset feed, on the same 100,000 posts. */
class OffsetPagingTrapTest extends ApiTest {

    static final String OFFSET_PAGE = Feed.FIRST.replace("LIMIT :n", "LIMIT :n OFFSET :skip");

    @AfterEach
    void removeNewPosts() {
        jdbc.sql("DELETE FROM posts WHERE body LIKE 'Test new post%'").update();
    }

    private List<Long> offsetPage(int page, int size) {
        return jdbc.sql(OFFSET_PAGE).param("n", size).param("skip", page * size).query((rs, i) -> rs.getLong("id")).list();
    }

    private static List<Long> ids(JsonNode page) {
        List<Long> ids = new ArrayList<>();
        page.get("posts").forEach(p -> ids.add(p.get("id").asLong()));
        return ids;
    }

    @Test
    void page2000ByOffsetReadsEveryPostBeforeIt() {
        // Page 2,000 of 20: the old feed reads and throws away 40,000 posts (and their authors) to return 20.
        long offset = rowsRead(OFFSET_PAGE, Map.of("n", 20, "skip", 40_000));
        // The same page by keyset: start after post 60,001, the last one on page 1,999.
        Instant at = jdbc.sql("SELECT created_at FROM posts WHERE id = 60001").query(OffsetDateTime.class).single().toInstant();
        long keyset = rowsRead(Feed.AFTER, Map.of("n", 21, "createdAt", OffsetDateTime.ofInstant(at, ZoneOffset.UTC), "id", 60001L));
        assertThat(offset).isGreaterThanOrEqualTo(40_020);
        assertThat(keyset).isLessThanOrEqualTo(100);
    }

    @Test
    void newPostsPushRepeatsOntoTheNextOffsetPage() throws Exception {
        List<Long> page1 = offsetPage(0, 20);
        JsonNode keysetPage1 = getFeed(null, 20);
        for (int i = 1; i <= 3; i++) {
            post("Test new post " + i);   // three people post while the reader looks at page 1
        }
        List<Long> page2 = offsetPage(1, 20);
        assertThat(page2.subList(0, 3)).isEqualTo(page1.subList(17, 20));   // the last three of page 1, again

        List<Long> keysetPage2 = ids(getFeed(keysetPage1.get("nextCursor").asString(), 20));
        assertThat(keysetPage2).doesNotContainAnyElementsOf(ids(keysetPage1));
        assertThat(keysetPage2.getFirst()).isEqualTo(99980);   // straight on from 99981, new posts or not
    }

    @Test
    void aCursorWithTheTimeAloneSkipsPostsFromTheSameSecond() throws Exception {
        JsonNode first = getFeed(null, 7);   // ends at post 99994; posts 99990 to 99993 share its second
        Instant last = Instant.parse(first.get("posts").get(6).get("createdAt").asString());
        List<Long> timeOnly = jdbc.sql(Feed.FIRST.replace("ORDER BY", "WHERE p.created_at < :createdAt ORDER BY"))
                .param("createdAt", OffsetDateTime.ofInstant(last, ZoneOffset.UTC)).param("n", 7).query((rs, i) -> rs.getLong("id")).list();
        assertThat(timeOnly.getFirst()).isEqualTo(99989);   // 99990 to 99993 never shown
        assertThat(ids(getFeed(first.get("nextCursor").asString(), 7))).startsWith(99993L, 99992L, 99991L, 99990L, 99989L);
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
./mvnw spring-boot:run      # the API on http://localhost:8080; the first start loads 100,000 posts
./mvnw test                 # all 11 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Follow the cursors by hand (needs `jq`), then compare with a deep offset in `psql`:

``` code
C=$(curl -s 'http://localhost:8080/feed?limit=3' | jq -r .nextCursor)
curl -s "http://localhost:8080/feed?limit=3&cursor=$C" | jq '.posts[].id'
docker compose exec postgres psql -U chaupal -d chaupal \
  -c "EXPLAIN ANALYZE SELECT id FROM posts ORDER BY created_at DESC, id DESC LIMIT 20 OFFSET 90000"
```

## Troubleshooting

| You see                                           | Cause                                                                                       | Fix                                                                            |
|---------------------------------------------------|---------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| Posts skipped at page boundaries                  | A cursor without the id, or a time rounded to milliseconds.                                 | Keep both, and the full microseconds.                                          |
| The seek query does a full sort                   | No index matching `(created_at, id)`, or the comparison written as two separate conditions. | One row-value comparison and a two-column index.                               |
| `400 Not a cursor from this feed` after a release | The cursor format changed.                                                                  | Keep reading the old version, or let clients start again: the message says so. |
| Different results with the time zone              | Binding a local timestamp against `timestamptz`.                                            | Bind `OffsetDateTime` in UTC, as `Feed` does.                                  |

## Project layout

``` tree
stations/066-social-feed-with-keyset-pagination/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/chaupal/feed/
│   ├── FeedController.java   ├── Cursor.java   ├── Feed.java   └── FeedApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__posts.sql, V2__demo_posts.sql
├── src/test/java/com/chaupal/feed/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/chaupal/feed/FeedController.java`

Does  
Checks the limit and decodes the cursor.

Why  
A bad cursor is a `400` before any query.

Without it  
A garbage cursor reaching SQL.

#### `src/main/java/com/chaupal/feed/Cursor.java`

Does  
Encodes and decodes the position: version, time in microseconds, id.

Why  
Opaque and versioned; parsed strictly.

Without it  
Clients building offsets or timestamps themselves.

- Microseconds, because PostgreSQL stores `timestamptz` to the microsecond: a millisecond cursor would round and skip or repeat posts.
- Not signed: a client can decode it, and can only ask for a position it could reach by scrolling.

#### `src/main/java/com/chaupal/feed/Feed.java`

Does  
The first page and the seek, one row more than asked.

Why  
The row-value comparison matches the index's order, so the page starts where the cursor points.

Without it  
`OFFSET`, and a count query to know about the next page.

#### `src/main/resources/db/migration/V1__posts.sql`

Does  
Tables, named constraints and the feed index.

Why  
`posts_feed (created_at, id)` read backwards is the feed.

Without it  
A sort of every post for every page.

#### `src/main/resources/db/migration/V2__demo_posts.sql`

4 authors and 100,000 posts, five per second.

#### `src/main/resources/application.yaml`

Problem details on.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/chaupal/feed/FeedApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                 | Result |
|---------------|-------------------------------------------------------|----------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found (empty page) | `FeedContractTest` (5)     | pass   |
| Every station | Reproduce the failure before the fix                  | `OffsetPagingTrapTest` (3) | pass   |
| Database      | Rollback and constraint tests against a real database | `PostDatabaseTest` (3)     | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.chaupal.feed.PostDatabaseTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.chaupal.feed.OffsetPagingTrapTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.chaupal.feed.FeedContractTest
[INFO] Tests run: 11, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/chaupal/feed/OffsetPagingTrapTest.java`

Written first: the cost of offset, repeats under new posts, and the time-only cursor.

#### `src/test/java/com/chaupal/feed/PostDatabaseTest.java`

Named constraints, the database's timestamp, and a rolled-back author.

#### `src/test/java/com/chaupal/feed/FeedContractTest.java`

The endpoint through HTTP, following real cursors.

#### `src/test/java/com/chaupal/feed/ApiTest.java`

Shared setup, the EXPLAIN row counter and a feed helper.

#### `src/test/java/com/chaupal/feed/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/chaupal/feed/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=AuthorFeedChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 11 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 14 tests pass (11 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## One author's posts

Add `author=kabir`: that author's posts, newest first, with the same cursor. Unknown author: `404`.

**Done when:** both tests in `AuthorFeedChallengeTest` pass.

Hints

- One more condition, `p.author_id = :author`, in both queries.
- For speed at scale, an index on `(author_id, created_at, id)`; not needed for the test.

#### `challenge/AuthorFeedChallengeTest.java`

``` code
package com.chaupal.feed;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /feed?author=kabir is one author's posts, newest first, with the same keyset cursor. An author
 * Chaupal does not know is 404.
 */
class AuthorFeedChallengeTest extends ApiTest {

    @Test
    void oneAuthorsPostsPageByPage() throws Exception {
        JsonNode first = json.readTree(mvc.perform(get("/feed").param("author", "kabir").param("limit", "3")).andReturn().getResponse().getContentAsString());
        assertThat(first.get("posts").findValuesAsString("author")).containsOnly("kabir");
        assertThat(first.get("posts").findValues("id")).extracting(JsonNode::asLong).containsExactly(99997L, 99993L, 99989L);
        JsonNode second = json.readTree(mvc.perform(get("/feed").param("author", "kabir").param("limit", "3").param("cursor", first.get("nextCursor").asString()))
                .andReturn().getResponse().getContentAsString());
        assertThat(second.get("posts").findValues("id")).extracting(JsonNode::asLong).containsExactly(99985L, 99981L, 99977L);
    }

    @Test
    void anUnknownAuthorIs404() throws Exception {
        mvc.perform(get("/feed").param("author", "nobody_here")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Pull to refresh

Every page also returns `topCursor` (its first post). `GET /feed/new?cursor=…` returns the posts made since, newest first.

**Done when:** the test in `PullToRefreshChallengeTest` passes.

Hints

- Seek the other way: `(created_at, id) > (:t, :id)`, ordered ascending so the limit keeps the posts right after the cursor; then reverse.
- A record can get a second constructor that fills `topCursor` from the first post.

#### `challenge/PullToRefreshChallengeTest.java`

``` code
package com.chaupal.feed;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/**
 * Challenge 2: every page also carries "topCursor", the position of its first post. GET /feed/new?cursor=<topCursor>
 * returns the posts made since, newest first (at most limit), with its own topCursor, for pull-to-refresh.
 */
class PullToRefreshChallengeTest extends ApiTest {

    @AfterEach
    void removeNewPosts() {
        jdbc.sql("DELETE FROM posts WHERE body LIKE 'Test new post%'").update();
    }

    @Test
    void onlyThePostsMadeSince() throws Exception {
        JsonNode page = getFeed(null, 20);
        for (int i = 1; i <= 3; i++) {
            post("Test new post " + i);
        }
        JsonNode fresh = json.readTree(mvc.perform(get("/feed/new").param("cursor", page.get("topCursor").asString())).andReturn().getResponse().getContentAsString());
        assertThat(fresh.get("posts").findValuesAsString("body")).containsExactly("Test new post 3", "Test new post 2", "Test new post 1");
        JsonNode again = json.readTree(mvc.perform(get("/feed/new").param("cursor", fresh.get("topCursor").asString())).andReturn().getResponse().getContentAsString());
        assertThat(again.get("posts")).isEmpty();
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Should the cursor be signed?

Anyone can decode the cursor and write their own. Here that only lets them start at any point in a public feed. When would it matter: a feed of private posts, a cursor that also carries filters or a user id, a cursor that expires? Compare an HMAC-signed cursor, an encrypted one, and a server-side cursor id stored for a few minutes.

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the cost of a deep offset, repeats under new posts, and a time-only cursor.
2.  Pick the order `(created_at, id)` and an index for it.
3.  Seek with a row-value comparison; fetch one extra row.
4.  Encode the position in an opaque, versioned cursor, parsed strictly.

## Design alternatives and trade-offs

| Approach                                                                               | What it costs                                                                | Verdict             |
|----------------------------------------------------------------------------------------|------------------------------------------------------------------------------|---------------------|
| Keyset on (created_at, id), opaque cursor                                              | No page numbers, no jumping.                                                 | Chosen              |
| `OFFSET`                                                                               | Slower each page; repeats and gaps under inserts.                            | The trap            |
| Cursor on time only                                                                    | Skips posts sharing a timestamp.                                             | The trap, version 2 |
| Cursor on id only                                                                      | Correct only if ids follow time exactly, which imports and clock skew break. | Fragile             |
| Two conditions instead of a row value: `created_at < t OR (created_at = t AND id < i)` | Same result; easier to get wrong; may plan worse.                            | Works               |

## Database design

| Object                                                                                     | What                           | Why                                                        |
|--------------------------------------------------------------------------------------------|--------------------------------|------------------------------------------------------------|
| `posts_feed`                                                                               | B-tree `(created_at, id)`      | The feed order, read backwards; the seek starts inside it. |
| `created_at`                                                                               | `timestamptz`, default `now()` | The database's clock, to the microsecond.                  |
| `posts_author_fk`, `posts_body_not_blank`, `authors_handle_unique`, `authors_handle_shape` | Constraints                    | No orphan or empty posts.                                  |

``` code
CREATE TABLE authors (
    id     BIGINT      PRIMARY KEY,
    handle VARCHAR(30) NOT NULL CONSTRAINT authors_handle_unique UNIQUE
                               CONSTRAINT authors_handle_shape CHECK (handle ~ '^[a-z0-9_]{3,30}$')
);

CREATE TABLE posts (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    author_id  BIGINT        NOT NULL CONSTRAINT posts_author_fk REFERENCES authors (id),
    body       VARCHAR(500)  NOT NULL CONSTRAINT posts_body_not_blank CHECK (btrim(body) <> ''),
    created_at TIMESTAMPTZ   NOT NULL DEFAULT now()
);
-- The feed's order, newest first: read backwards, (created_at, id) finds "the posts after this one" directly.
CREATE INDEX posts_feed ON posts (created_at, id);
```

# 3 · Go deeper: Production

Deleted posts  
A cursor still works if its post is deleted: it is a position, not a lookup.

Edits  
Ordering by a column that changes ("updated at") moves posts between pages; order by something that never changes.

Clocks  
With several app servers, use the database's `now()` (as here), not each server's clock.

Caching  
The first page changes constantly; later pages by cursor barely do, and cache well.

# 3 · Go deeper: Interview

## Interview takeaways

Why does OFFSET get slower?

The database must produce and discard every skipped row in order; page N costs N × page size rows.

What is keyset pagination?

The next page is "rows after this key" in a fixed order, answered by an index seek; its cost does not grow with depth.

Why include the id in the cursor?

To break ties: several rows can share a timestamp, and the cursor must name exactly one position.

Why make the cursor opaque?

Clients cannot depend on its contents, so the server can change them; it also stops clients building offsets.

What does keyset pagination give up?

Jumping to page N and showing "page 3 of 100"; it suits feeds and exports, not numbered admin lists.

## Self-check rubric

| Area        | Meets the bar                        | Above the bar                |
|-------------|--------------------------------------|------------------------------|
| Correctness | All 11 tests pass.                   | You read both saved plans.   |
| Keyset      | Row-value seek and a matching index. | Why microseconds matter.     |
| Cursors     | Opaque, with a tie-breaker.          | When to sign them.           |
| Trade-offs  | Knows the cost of OFFSET.            | Knows what keyset cannot do. |

# 3 · Go deeper: Review

## No reviewer view for this station

This station has no flawed version to review. Use this checklist on any feed or export:

- Does any page use `OFFSET` on a list that grows or changes?
- Does the cursor hold every column of the order, including a unique one?
- Does an index match the order, in the same column order?
- Is the cursor parsed strictly, and does a bad one give a `400`?
