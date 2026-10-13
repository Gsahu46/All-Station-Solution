# Station 010 · Threaded comment replies

Foundations · 0–1 years · Core · Social · Types: none

Spring Boot 4.1.1 · Java 25 · Spring MVC · HashMap · recursion with a limit · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Three posts are fixed in the code: a normal discussion, one reply chain 100,000 comments deep (a bot replying to itself), and an empty post. Everything is in memory.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 13 tests.

# 1 · Understand

## The problem in real life

1.  **Comments are stored flat**

    Each reply just remembers which comment it answers. The app showed them in storage order, so replies sometimes appeared above the comment they answered.

2.  **A bot replies to itself 100,000 times**

    The new "nested replies" feature built the tree with recursion that went as deep as the data. On that thread the server ran out of stack and every reader got an error page.

3.  **The fix**

    Group replies by parent with one map, nest them up to a depth limit, and below the limit only count them, without recursion.

Data from users has no natural limits. Any code whose depth or size follows the data needs a limit of its own.

## What are we building?

`GET /posts/{id}/comment-tree?maxDepth=5`: the post's comments as a tree, replies under the comment they answer, oldest first. Below `maxDepth`, replies are not nested; the last shown comment says how many are hidden.

## An everyday analogy

A wedding invitation list grows as "Sharma family → Rahul's family → Rahul's cousins → …". To print it, you first sort every name into a folder labelled with whose guest they are. Then you print a few levels deep and write "+ 37 more" for the rest, instead of following every branch to the end.

## How it works in 4 steps

1.  **Group**: one pass over the comments puts each into a map under its parent's id. Top-level comments, and replies whose parent is missing, go in a separate list.
2.  **Sort** each group oldest first (ties by id).
3.  **Nest** from the top, one level at a time, up to `maxDepth` levels.
4.  **Count** what is below the last level with a loop and a to-do list, not recursion: `moreReplies`.

Check yourself: recursion is used in step 3 too. Why is that safe and step 4 not?

Step 3 stops at `maxDepth`, at most 10 levels, whatever the data. Step 4 must go all the way down, and that depth comes from the data: 100,000 on post 2. So step 4 uses a loop with its own list of comments still to visit.

## What this station is not

- **No database.** Comments are fixed in memory; post 2's chain is generated at start-up.
- **No posting.** Station 007 covers adding comments safely.
- **No paging of wide threads.** A comment with 5,000 replies returns all 5,000.

## Key terms

| Term                        | Simple meaning                                                                         | Everyday example                                       | In this project                                  |
|-----------------------------|----------------------------------------------------------------------------------------|--------------------------------------------------------|--------------------------------------------------|
| **Flat list**               | Every comment stored side by side, each with the id of the comment it answers.         | A pile of letters, each saying "in reply to letter 4". | `parentId` on each comment.                      |
| **Tree**                    | Comments nested inside the comments they answer.                                       | A family tree.                                         | `replies` inside each node.                      |
| **Map lookup by parent id** | Group replies by the comment they answer, once, so finding them later is instant.      | Sorting letters into folders by "in reply to".         | `Map<Long, List<Comment>>`                       |
| **Recursion**               | A method that calls itself for a smaller piece of the problem.                         | Opening a box to find a smaller box inside.            | Building each node's replies.                    |
| **Stack overflow**          | The crash when recursion goes deeper than the thread's memory for method calls allows. | Boxes nested so deep you run out of hands.             | `StackOverflowError` on the 100,000-deep thread. |
| **Depth limit**             | Stop nesting after N levels and show "n more replies" instead.                         | "Continue this thread →" on forums.                    | `maxDepth`, 1 to 10.                             |
| **Siblings**                | Replies to the same comment.                                                           | Children of the same parents.                          | Ordered oldest first, then by id.                |

# 2 · Build: Spec

## Business problem

**Chaupal** (the forum from station 007) stores comments flat. Its app showed them in storage order, so replies sometimes came before the comments they answered. The first version of "nested replies" fixed the order but crashed on a thread where a misconfigured bot had replied to itself 100,000 times: the recursive builder threw `StackOverflowError` and the post became unreadable for everyone.

## Acceptance criteria

1.  **Given** a post, **then** top-level comments come oldest first, and each reply sits under the comment it answers, oldest first; equal times are ordered by id.
2.  **Given** `maxDepth=N`, **then** at most N levels are nested; a comment on level N has empty `replies` and `moreReplies` = the number of comments below it.
3.  **Given** the 100,000-deep thread, **then** `200`, quickly, with `moreReplies` counting the rest.
4.  **Given** a reply whose parent is gone, **then** it is shown at the top level. **Given** comments in a loop (corrupt data), **then** the request still finishes.
5.  **Given** `maxDepth` outside 1–10, **then** `400`. **Given** an unknown post, **then** `404`. **Given** a post with no comments, **then** an empty list.

## Requirements

- One pass to group by parent id; no searching the list for each comment's replies.
- No recursion whose depth depends on the data.
- `maxDepth`: default 5, 1 to 10.
- Errors are RFC 9457 problems.

## Learning objectives

- Build a tree from a flat list with a map from parent id to children.
- Order siblings with a comparator and a tie-breaker.
- Explain why unbounded recursion fails on user data, and bound it.
- Rewrite a recursive count as a loop with an explicit stack.
- Handle broken data: missing parents and loops.

# 2 · Build: API contract

## Endpoint

| Method | Path                                    | Purpose                                                                   |
|--------|-----------------------------------------|---------------------------------------------------------------------------|
| `GET`  | `/posts/{postId}/comment-tree?maxDepth` | The post's comments as a tree, up to `maxDepth` levels (default 5, 1–10). |

## Each node

| Field                               | Meaning                                                                             |
|-------------------------------------|-------------------------------------------------------------------------------------|
| `id`, `author`, `text`, `createdAt` | The comment.                                                                        |
| `replies`                           | Its replies, oldest first, each a node of the same shape. Empty at the depth limit. |
| `moreReplies`                       | How many comments are below this one but not shown (0 above the limit).             |

## Status codes

| Status | When                                                      |
|--------|-----------------------------------------------------------|
| 200    | The post exists (an empty `comments` list if it has none) |
| 400    | `maxDepth` outside 1–10, or not a number                  |
| 404    | No such post                                              |

## Captured examples

Captured with curl from the running app on 13 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: the chai discussion

**Why:** two top-level comments; the deepest reply ("Closed on Mondays") is 5 levels down, within the default limit. Comments 2 and 3 were posted in the same minute, so they are ordered by id.

Request

``` code
GET /posts/1/comment-tree HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 1126

{
  "postId": 1,
  "maxDepth": 5,
  "comments": [
    {
      "id": 1,
      "author": "asha",
      "text": "Best cutting chai near FC Road?",
      "createdAt": "2026-10-12T04:30:00Z",
      "replies": [
        {
          "id": 2,
          "author": "ravi",
          "text": "Amruttulya, every time.",
          "createdAt": "2026-10-12T04:32:00Z",
          "replies": [
            {
              "id": 4,
              "author": "asha",
              "text": "The one near the college?",
              "createdAt": "2026-10-12T04:34:00Z",
              "replies": [
                {
                  "id": 5,
                  "author": "ravi",
                  "text": "Yes, opposite the gate.",
                  "createdAt": "2026-10-12T04:35:00Z",
                  "replies": [
                    {
                      "id": 8,
                      "author": "tara",
                      "text": "Closed on Mondays though.",
                      "createdAt": "2026-10-12T04:38:00Z",
                      "replies": [],
                      "moreReplies": 0
                    }
                  ],
                  "moreReplies": 0
                }
              ],
              "moreReplies": 0
            }
          ],
          "moreReplies": 0
        },
        {
          "id": 3,
          "author": "kabir",
          "text": "Yewale is better.",
          "createdAt": "2026-10-12T04:32:00Z",
          "replies": [
            {
              "id": 7,
              "author": "kabir",
              "text": "And cheaper.",
              "createdAt": "2026-10-12T04:37:00Z",
              "replies": [],
              "moreReplies": 0
            }
          ],
          "moreReplies": 0
        }
      ],
      "moreReplies": 0
    },
    {
      "id": 6,
      "author": "meera",
      "text": "Anyone tried the new place in Baner?",
      "createdAt": "2026-10-12T04:36:00Z",
      "replies": [
        {
          "id": 9,
          "author": "asha",
          "text": "Not yet!",
          "createdAt": "2026-10-12T04:39:00Z",
          "replies": [],
          "moreReplies": 0
        }
      ],
      "moreReplies": 0
    }
  ]
}
```

### Case 2: only two levels

**Why:** level-2 comments show no replies, and `moreReplies` says how many are hidden below each.

Request

``` code
GET /posts/1/comment-tree?maxDepth=2 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 648

{
  "postId": 1,
  "maxDepth": 2,
  "comments": [
    {
      "id": 1,
      "author": "asha",
      "text": "Best cutting chai near FC Road?",
      "createdAt": "2026-10-12T04:30:00Z",
      "replies": [
        {
          "id": 2,
          "author": "ravi",
          "text": "Amruttulya, every time.",
          "createdAt": "2026-10-12T04:32:00Z",
          "replies": [],
          "moreReplies": 3
        },
        {
          "id": 3,
          "author": "kabir",
          "text": "Yewale is better.",
          "createdAt": "2026-10-12T04:32:00Z",
          "replies": [],
          "moreReplies": 1
        }
      ],
      "moreReplies": 0
    },
    {
      "id": 6,
      "author": "meera",
      "text": "Anyone tried the new place in Baner?",
      "createdAt": "2026-10-12T04:36:00Z",
      "replies": [
        {
          "id": 9,
          "author": "asha",
          "text": "Not yet!",
          "createdAt": "2026-10-12T04:39:00Z",
          "replies": [],
          "moreReplies": 0
        }
      ],
      "moreReplies": 0
    }
  ]
}
```

### Case 3: the 100,000-deep thread

**Why:** three levels are nested, then the rest is counted with a loop: `moreReplies: 99997`. No stack overflow, no error page.

Request

``` code
GET /posts/2/comment-tree?maxDepth=3 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 385

{
  "postId": 2,
  "maxDepth": 3,
  "comments": [
    {
      "id": 200001,
      "author": "echo-bot",
      "text": "Reply 0",
      "createdAt": "2026-10-12T04:30:00Z",
      "replies": [
        {
          "id": 200002,
          "author": "echo-bot",
          "text": "Reply 1",
          "createdAt": "2026-10-12T04:30:01Z",
          "replies": [
            {
              "id": 200003,
              "author": "echo-bot",
              "text": "Reply 2",
              "createdAt": "2026-10-12T04:30:02Z",
              "replies": [],
              "moreReplies": 99997
            }
          ],
          "moreReplies": 0
        }
      ],
      "moreReplies": 0
    }
  ]
}
```

### Case 4: maxDepth=1000

**Why:** the limit is part of the contract; a client cannot switch it off. `400`.

Request

``` code
GET /posts/1/comment-tree?maxDepth=1000 HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "The request parameters are invalid.",
  "instance": "/posts/1/comment-tree",
  "status": 400,
  "title": "Bad Request",
  "errors": {
    "maxDepth": "must be less than or equal to 10"
  }
}
```

### Case 5: unknown post

**Why:** `404`.

Request

``` code
GET /posts/99/comment-tree HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No post has this id.",
  "instance": "/posts/99/comment-tree",
  "status": 404,
  "title": "Post not found"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                             | What happens                     | Proved by                                                                                |
|--------------------------------------------------|----------------------------------|------------------------------------------------------------------------------------------|
| Normal thread                                    | Nested, oldest first, ties by id | `repliesAreNestedUnderTheCommentTheyAnswerOldestFirst`, `siblingsAreOldestFirstThenById` |
| Depth limit                                      | Replies counted, not shown       | `atTheDepthLimitRepliesAreCountedNotShown`, `maxDepthOneShowsOnlyTopLevelComments`       |
| 100,000-deep thread over HTTP                    | `200`, `moreReplies: 99997`      | `theRealEndpointStopsAtTheDepthLimitAndCountsWhatIsBelow`                                |
| Counting 100,000 levels directly                 | No recursion, no overflow        | `countingBelowAHundredThousandLevelsUsesNoRecursion`                                     |
| 5,000 replies to one comment                     | All kept                         | `aWideThreadKeepsEveryReply`                                                             |
| Parent deleted                                   | Reply shown at the top           | `aReplyWhoseParentIsGoneIsShownAtTheTop`                                                 |
| Comments in a loop; a comment replying to itself | Finishes in time; loop left out  | `commentsInALoopDoNotHangTheBuilder`                                                     |
| No comments                                      | Empty list                       | `aPostWithNoCommentsIsAnEmptyTree`                                                       |
| maxDepth 0, 11, 100000, -1, "deep"               | `400`                            | `maxDepthOutsideOneToTenIs400`                                                           |
| Unknown post                                     | `404`                            | `anUnknownPostIs404`                                                                     |

## The trap

Plausible but wrong

Unbounded recursion on deep threads, crashing with `StackOverflowError`.

"A node's replies are the nodes of its children" is a beautiful three-line method, and every normal thread works. The first test runs it on post 2: `StackOverflowError`. In a controller that is a `500` for every reader of the post. The second test asks the real endpoint for the same thread and gets an answer. Rewriting `countBelow` recursively was tried while building: 2 tests went red with `StackOverflowError`.

``` code
package com.chaupal.threads;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: it reproduces the crash before the fix.
 * Post 2 is one reply chain, 100,000 comments deep.
 */
class UnboundedRecursionTrapTest extends ApiTest {

    @Autowired
    CommentStore store;

    /** The "before" code: nest every reply inside its parent, as deep as the data goes. Kept only in tests. */
    static Node naive(Comment c, Map<Long, List<Comment>> children) {
        List<Node> replies = children.getOrDefault(c.id(), List.of()).stream().map(r -> naive(r, children)).toList();
        return new Node(c.id(), c.author(), c.text(), c.createdAt(), replies, 0);
    }

    @Test
    void recursionWithoutALimitOverflowsTheStackOnADeepThread() {
        List<Comment> chain = store.forPost(2).orElseThrow();
        Map<Long, List<Comment>> children = chain.stream().filter(c -> c.parentId() != null)
                .collect(Collectors.groupingBy(Comment::parentId));
        Comment root = chain.getFirst();
        assertThatThrownBy(() -> naive(root, children)).isInstanceOf(StackOverflowError.class); // a 500 for every reader
    }

    @Test
    void theRealEndpointStopsAtTheDepthLimitAndCountsWhatIsBelow() throws Exception {
        mvc.perform(get("/posts/2/comment-tree").param("maxDepth", "3"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.comments[0].text").value("Reply 0"))
                .andExpect(jsonPath("$.comments[0].replies[0].replies[0].text").value("Reply 2"))
                .andExpect(jsonPath("$.comments[0].replies[0].replies[0].replies").isEmpty())
                .andExpect(jsonPath("$.comments[0].replies[0].replies[0].moreReplies").value(99_997));
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
./mvnw test                 # all 13 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

``` code
curl "http://localhost:8080/posts/1/comment-tree"
curl "http://localhost:8080/posts/1/comment-tree?maxDepth=2"

# The thread that crashed the old code: expect "moreReplies":99997
curl "http://localhost:8080/posts/2/comment-tree?maxDepth=3"
```

Then copy the trap test's `naive` method into a scratch class and call it on post 2 yourself: seeing the `StackOverflowError` once makes the lesson stick.

## Troubleshooting

| You see                            | Cause                        | Fix                                                      |
|------------------------------------|------------------------------|----------------------------------------------------------|
| `400`                              | `maxDepth` outside 1–10.     | Use a value from 1 to 10.                                |
| Only part of the URL is used       | The shell cut at `?` or `&`. | Put the URL in double quotes.                            |
| `release version 25 not supported` | Maven is using an older JDK. | Point `JAVA_HOME` at JDK 25, or add `-Djava.version=21`. |

## Project layout

``` tree
stations/010-threaded-comment-replies/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/chaupal/threads/
│   ├── CommentTreeController.java   ├── ThreadBuilder.java   ├── CommentStore.java
│   ├── Comment.java                 ├── Node.java            ├── ApiErrors.java
│   └── ThreadsApplication.java
├── src/test/java/com/chaupal/threads/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/chaupal/threads/CommentTreeController.java`

Does  
Reads `maxDepth` (1–10), finds the post, and returns the tree.

Why  
The limit is checked at the door, so no request can ask for unlimited depth.

Without it  
No endpoint; without the cap, `maxDepth=100000` would bring the overflow back.

#### `src/main/java/com/chaupal/threads/ThreadBuilder.java`

Does  
Groups comments by parent id, sorts siblings, nests up to `maxDepth`, and counts the rest with a loop.

Why  
Each step has a cost that does not depend on how deep users go.

Without it  
The trap.

- Replies whose parent is missing become top-level comments, so nothing is silently lost.
- `countBelow` keeps its own to-do list (`ArrayDeque`) instead of using the call stack.
- Comments in a loop never have a top-level ancestor, so they are never visited and cannot hang the request.

#### `src/main/java/com/chaupal/threads/CommentStore.java`

Does  
The three posts. Post 1 is stored newest first on purpose; post 2's chain is generated.

Why  
Realistic and hostile data in one place.

Without it  
Nothing to show.

#### `src/main/java/com/chaupal/threads/Comment.java`

A stored comment, with `parentId` (null at the top).

#### `src/main/java/com/chaupal/threads/Node.java`

A comment in the tree, with `replies` and `moreReplies`.

#### `src/main/java/com/chaupal/threads/ApiErrors.java`

Adds an `errors` map to parameter validation failures (as in station 002).

#### `src/main/java/com/chaupal/threads/ThreadsApplication.java`

Standard Spring Boot entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                               | Test class                       | Result |
|---------------|-------------------------------------------|----------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found  | `CommentTreeContractTest` (6)    | pass   |
| Every station | Reproduce the failure before the fix      | `UnboundedRecursionTrapTest` (2) | pass   |
| This station  | The builder on broken, deep and wide data | `ThreadBuilderTest` (5)          | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.chaupal.threads.UnboundedRecursionTrapTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.chaupal.threads.ThreadBuilderTest
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.chaupal.threads.CommentTreeContractTest
[INFO] Tests run: 13, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/chaupal/threads/UnboundedRecursionTrapTest.java`

Written first: the naive builder overflows on post 2; the endpoint answers.

#### `src/test/java/com/chaupal/threads/CommentTreeContractTest.java`

Shape, order, depth limits and every refusal.

#### `src/test/java/com/chaupal/threads/ThreadBuilderTest.java`

Missing parents, loops (with a 2-second timeout), ties, 100,000 deep, 5,000 wide.

#### `src/test/java/com/chaupal/threads/ApiTest.java`

Shared setup: the whole app through MockMvc.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/chaupal/threads/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=TotalRepliesChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 13 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 18 tests pass (13 station tests and 5 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## "12 replies" on every comment

Add `totalReplies` to every node: all comments below it at any depth, shown or not. It must work on the 100,000-deep thread.

**Done when:** both tests in `TotalRepliesChallengeTest` pass, and the station's tests still pass.

Hints

- `countBelow` already counts without recursion; call it for every node you build.
- Adding a field to the `Node` record breaks `new Node(...)` calls in the tests: keep a six-argument constructor.
- Notice the cost: a node and its parent count the same comments again. Fine for 10 levels; think about it for larger trees.

#### `challenge/TotalRepliesChallengeTest.java`

``` code
package com.chaupal.threads;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/** Challenge 1: every comment shows how many replies it has in total, at any depth ("12 replies"). */
class TotalRepliesChallengeTest extends ApiTest {

    @Test
    void everyNodeCountsAllItsReplies() throws Exception {
        mvc.perform(get("/posts/1/comment-tree"))
                .andExpect(jsonPath("$.comments[0].totalReplies").value(6))
                .andExpect(jsonPath("$.comments[0].replies[0].totalReplies").value(3))
                .andExpect(jsonPath("$.comments[0].replies[1].totalReplies").value(1))
                .andExpect(jsonPath("$.comments[1].totalReplies").value(1))
                .andExpect(jsonPath("$.comments[1].replies[0].totalReplies").value(0));
    }

    @Test
    void theDeepThreadIsCountedWithoutCrashing() throws Exception {
        mvc.perform(get("/posts/2/comment-tree").param("maxDepth", "2"))
                .andExpect(jsonPath("$.comments[0].totalReplies").value(99_999))
                .andExpect(jsonPath("$.comments[0].replies[0].totalReplies").value(99_998));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Continue this thread

Behind "moreReplies" the app shows "Continue this thread". Add an optional `rootId`: the tree then starts at that comment. An unknown comment, or one from another post, is `404`.

**Done when:** all three tests in `ContinueThreadChallengeTest` pass.

Hints

- The grouping by parent does not change; only the starting point does.
- Look the root up in this post's comments only, or one post could read another's thread.

#### `challenge/ContinueThreadChallengeTest.java`

``` code
package com.chaupal.threads;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: "Continue this thread": rootId starts the tree at one comment, so the app can open what was cut off. */
class ContinueThreadChallengeTest extends ApiTest {

    @Test
    void theTreeStartsAtTheGivenComment() throws Exception {
        mvc.perform(get("/posts/2/comment-tree").param("rootId", "200006").param("maxDepth", "2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.comments[0].id").value(200006))
                .andExpect(jsonPath("$.comments[0].replies[0].id").value(200007))
                .andExpect(jsonPath("$.comments[0].replies[0].moreReplies").value(99_993));
    }

    @Test
    void aSmallSubtreeOnPostOne() throws Exception {
        mvc.perform(get("/posts/1/comment-tree").param("rootId", "2"))
                .andExpect(jsonPath("$.comments[0].replies[0].replies[0].replies[0].text").value("Closed on Mondays though."));
    }

    @Test
    void anUnknownCommentOrOneFromAnotherPostIs404() throws Exception {
        mvc.perform(get("/posts/1/comment-tree").param("rootId", "12345")).andExpect(status().isNotFound());
        mvc.perform(get("/posts/1/comment-tree").param("rootId", "200006")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## A post with 2 lakh comments

A viral post has 2 lakh comments. Loading all of them for every reader to build a 5-level tree is wasteful. Which comments would you load first, and how would you page through top-level comments? How could a database help (for example, storing each comment's depth and its top-level ancestor)? What would "continue this thread" load?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the naive recursive builder overflows on 100,000 levels.
2.  Group by parent id in one pass; treat missing parents as top level.
3.  Sort siblings with a comparator and a tie-breaker.
4.  Nest with recursion capped by `maxDepth`; count below the cap with a loop.
5.  Test broken data: missing parents and loops.

## Design alternatives and trade-offs

| Approach                                             | What it costs                                                                                       | Verdict        |
|------------------------------------------------------|-----------------------------------------------------------------------------------------------------|----------------|
| Map by parent id, capped nesting, iterative counting | One pass to group; work below the cap is a loop.                                                    | Chosen         |
| Recursion as deep as the data                        | `StackOverflowError` on deep threads (the trap).                                                    | Wrong          |
| For each comment, search the list for its replies    | Correct but O(n²): 100,000 comments means 10 billion comparisons.                                   | Too slow       |
| Increase the thread stack size (`-Xss`)              | Moves the crash further away; a deeper thread still crashes, and every thread pays the memory.      | Not a fix      |
| Return the flat list; let the app build the tree     | Moves the same problem to every client, on weaker devices.                                          | Possible       |
| Recursive SQL (`WITH RECURSIVE`) with a depth column | The database does the walk and can stop at a depth; the right tool once comments are in a database. | Later stations |

## Database design

None in this station. A table would have `id`, `post_id`, `parent_id` (nullable, foreign key to `id`), `created_at`, and an index on `(post_id, parent_id, created_at)` so each group of siblings comes back already sorted.

# 3 · Go deeper: Production

Reliability  
One hostile thread must not make a post unreadable. Every loop or recursion that follows user data needs a limit, and a test at that limit.

Performance  
Grouping is one pass; nesting is bounded. Very wide threads (thousands of replies to one comment) are the next limit: page them.

Security  
A depth or size parameter is an attack surface: the cap of 10 is enforced by the server, whatever the client asks.

Data quality  
Missing parents and loops are real in old data. Show what you can, never hang, and log loops for someone to repair.

# 3 · Go deeper: Interview

## Interview takeaways

How do you build a tree from a flat list of (id, parentId)?

One pass to group children by parentId in a HashMap; roots are those with no parent (or a missing one). Then walk from the roots, looking up each node's children in the map. O(n) to group, instead of O(n²) searching.

Why did the recursive version crash?

Each recursive call uses a stack frame. The JVM thread stack is limited (often around 1 MB), so tens of thousands of nested calls exceed it and throw StackOverflowError. The depth came from user data, so it had no limit.

How do you turn recursion into a loop?

Keep your own stack (an ArrayDeque) of work still to do. Pop one item, process it, push its children. The depth now lives in heap memory, which is much larger, instead of the call stack.

Why still use recursion for nesting?

Because its depth is capped by maxDepth (at most 10), not by the data. Bounded recursion is fine and easier to read.

What can go wrong with real comment data?

Parents deleted (orphans), loops from bad migrations or bugs, and very wide or deep threads. Decide what to show for each and test it.

## Self-check rubric

| Area        | Meets the bar                                        | Above the bar                                               |
|-------------|------------------------------------------------------|-------------------------------------------------------------|
| Correctness | All 13 tests pass.                                   | You can say which tests fail with a recursive `countBelow`. |
| Design      | Grouping by map; capped nesting.                     | You can explain why `-Xss` is not a fix.                    |
| Tests       | A test at 100,000 levels.                            | You added a test for another kind of broken data.           |
| Explanation | You can turn a small recursion into a loop on paper. | You can sketch the SQL version.                             |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any code that walks user data:

- Does any recursion or loop depth depend on user data? What caps it?
- Is there a nested loop that searches a list for every item?
- What happens with a missing parent, or a loop?
- Is there a test at the limit, not just below it?
