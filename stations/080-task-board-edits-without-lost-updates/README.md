# Station 080 · Task board edits without lost updates

Working Systems · 0–2 years · Core · SaaS · Types: Database, Concurrency

Spring Boot 4.1.1 · Java 25 · Spring Data JDBC @Version · ETag, If-Match, If-None-Match · PostgreSQL 17 trigger · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The board and its tasks are demo data, not Taskloom's. There is no sign-in in this station: editors are named only in the stories.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 14 tests.

# 1 · Understand

## The problem in real life

1.  **Two managers, one card**

    Meera moved "Write the press release" to doing. At the same moment Kabir reassigned it to Ravi.

2.  **One change vanished**

    Kabir's screen still showed the card as open. His save sent the whole card back, and Meera's change disappeared. Nobody was told.

3.  **The fix**

    Every card has a version. A save names the version it was based on, and only one save per version can win; the other editor is told to read again, and nothing is lost.

A save must say what it was based on. Otherwise the server cannot know it is overwriting someone.

## What are we building?

`GET /tasks/{id}` with an ETag, and `PUT /tasks/{id}` that saves only with the ETag of the current version.

## An everyday analogy

A shared document that says "this was changed while you were editing" instead of saving over the other person's work.

## How it works in 4 steps

1.  **Read**: the card comes with `ETag: "0"`.
2.  **Save**: the editor sends `If-Match: "0"` with the new card.
3.  **Check and write at once**: `UPDATE ... WHERE id = 1 AND version = 0`; the version becomes 1.
4.  **The other editor** still sends `"0"`: no row matches, `412`; they read again and save on top.

Check yourself: Meera and Kabir press Save in the same millisecond. Can both win?

No. The check is inside the UPDATE itself; PostgreSQL lets one of them change the row, and the other finds no row at version 0 any more. `tenEditsOfTheSameVersionAtOnceSaveExactlyOne` runs ten at once: one 200, nine 412.

## What this station is not

- **No merging.** A stale save is refused, not merged (Practice, challenge 3).
- **No live editing.** Real-time collaboration needs other tools.
- **No sign-in.** Stations 071 to 079 cover that.

## Key terms

| Term                   | Simple meaning                                                                            | Everyday example                                                  | In this project    |
|------------------------|-------------------------------------------------------------------------------------------|-------------------------------------------------------------------|--------------------|
| **Lost update**        | Two people edit the same thing; the later save quietly replaces the earlier one.          | Two people editing a printed list and handing back their copies.  | the old board      |
| **Version**            | A number that goes up with every change.                                                  | The edition number on a timetable.                                | `tasks.version`    |
| **ETag**               | A label for one exact version, sent with a response.                                      | "Timetable, edition 3".                                           | `ETag: "3"`        |
| **If-Match**           | "Save this only if it is still that version."                                             | "Replace edition 3 with mine, if 3 is still current."             | on every PUT       |
| **Optimistic locking** | No lock while people edit; the save checks the version and refuses if it moved.           | Checking the edition at the counter, not reserving the timetable. | `@Version`         |
| **412, 409, 428**      | 412: your copy is old. 409: your change breaks a rule. 428: say which version you edited. | "Old edition", "that slot is taken", "which edition?"             | the three refusals |

# 2 · Build: Spec

## Business problem

**Taskloom** (a fictional team tool): two managers edit one task at once and one change silently disappears.

## Acceptance criteria

Demo board "launch": task 1 "Write the press release" and task 2 "Book the venue", both at version 0.

1.  **Given** a read, **then** the task and `ETag: "version"`.
2.  **Given** a save with the current ETag, **then** `200` and the next ETag.
3.  **Given** a save with an older ETag, **then** `412`, and the task is unchanged.
4.  **Given** a save without `If-Match`, **then** `428`.
5.  **Given** the current ETag but a title another task on the board has, **then** `409`.
6.  **Given** ten saves of one version at once, **then** exactly one is saved.

## Requirements

- The version check and the write are one statement.
- Every writer must move the version on by one: the database enforces it.
- A save and its activity row are one transaction.

## Learning objectives

- Explain the lost update and reproduce it.
- Use `@Version` and ETags with `If-Match`.
- Choose between 409, 412 and 428.
- Prove it with a real parallel test.

# 2 · Build: API contract

## Endpoints

| Method | Path          | Purpose                                                                            |
|--------|---------------|------------------------------------------------------------------------------------|
| `GET`  | `/tasks/{id}` | The task, with `ETag: "version"`. With `If-None-Match` equal to it: `304`.         |
| `PUT`  | `/tasks/{id}` | `If-Match: "version"` and the whole task `{title, description, status, assignee}`. |

## Status codes

| Status    | When                                                                             |
|-----------|----------------------------------------------------------------------------------|
| 200 / 304 | Read or saved / unchanged since the ETag you have                                |
| 400       | A field missing, empty, too long, or an unknown status                           |
| 404       | No such task                                                                     |
| 409       | Your copy is current, but the edit clashes with the board (a title already used) |
| 412       | Your copy is old (or the ETag is not one of ours): read again                    |
| 428       | No `If-Match`: the server cannot tell what you edited                            |

## Captured examples

Captured with curl from the running app on 21 Oct 2026, in this order. JSON bodies are indented for reading; `Date`, connection and standard security headers are left out.

### Case 1: both managers read the card

**Why:** version 0, `ETag: "0"`.

Request

``` code
GET /tasks/1 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
ETag: "0"
Content-Type: application/json

{
  "id": 1,
  "board": "launch",
  "title": "Write the press release",
  "description": "One page, two quotes.",
  "status": "open",
  "assignee": "asha",
  "version": 0
}
```

### Case 2: Meera saves first

**Why:** `If-Match: "0"` matches: saved, `ETag: "1"`.

Request

``` code
PUT /tasks/1 HTTP/1.1
Content-Type: application/json
If-Match: "0"

{
  "title": "Write the press release",
  "description": "One page, two quotes.",
  "status": "doing",
  "assignee": "asha"
}
```

Response

``` code
HTTP/1.1 200 
ETag: "1"
Content-Type: application/json

{
  "id": 1,
  "board": "launch",
  "title": "Write the press release",
  "description": "One page, two quotes.",
  "status": "doing",
  "assignee": "asha",
  "version": 1
}
```

### Case 3: Kabir saves his old copy

**Why:** still `"0"`: `412`. Meera's change stays.

Request

``` code
PUT /tasks/1 HTTP/1.1
Content-Type: application/json
If-Match: "0"

{
  "title": "Write the press release",
  "description": "One page, two quotes.",
  "status": "open",
  "assignee": "ravi"
}
```

Response

``` code
HTTP/1.1 412 
Content-Type: application/problem+json

{
  "detail": "Someone changed this task after you read it. Read it again, then edit.",
  "instance": "/tasks/1",
  "status": 412,
  "title": "Precondition Failed"
}
```

### Case 4: Kabir reads again

**Why:** he sees Meera's change and `ETag: "1"`.

Request

``` code
GET /tasks/1 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
ETag: "1"
Content-Type: application/json

{
  "id": 1,
  "board": "launch",
  "title": "Write the press release",
  "description": "One page, two quotes.",
  "status": "doing",
  "assignee": "asha",
  "version": 1
}
```

### Case 5: Kabir saves on top

**Why:** both changes kept, `ETag: "2"`.

Request

``` code
PUT /tasks/1 HTTP/1.1
Content-Type: application/json
If-Match: "1"

{
  "title": "Write the press release",
  "description": "One page, two quotes.",
  "status": "doing",
  "assignee": "ravi"
}
```

Response

``` code
HTTP/1.1 200 
ETag: "2"
Content-Type: application/json

{
  "id": 1,
  "board": "launch",
  "title": "Write the press release",
  "description": "One page, two quotes.",
  "status": "doing",
  "assignee": "ravi",
  "version": 2
}
```

### Case 6: a save without If-Match

**Why:** `428`.

Request

``` code
PUT /tasks/1 HTTP/1.1
Content-Type: application/json

{
  "title": "Write the press release",
  "description": "One page, two quotes.",
  "status": "done",
  "assignee": "ravi"
}
```

Response

``` code
HTTP/1.1 428 
Content-Type: application/problem+json

{
  "detail": "Send If-Match with the ETag from GET /tasks/1",
  "instance": "/tasks/1",
  "status": 428,
  "title": "Precondition Required"
}
```

### Case 7: the current ETag, a title already on the board

**Why:** `409`: not a stale copy, a clash.

Request

``` code
PUT /tasks/1 HTTP/1.1
Content-Type: application/json
If-Match: "2"

{
  "title": "Book the venue",
  "description": "One page, two quotes.",
  "status": "doing",
  "assignee": "ravi"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "A task with this title is already on the board",
  "instance": "/tasks/1",
  "status": 409,
  "title": "Conflict"
}
```

### Case 8: the board polls with the ETag it has

**Why:** `304`, no body.

Request

``` code
GET /tasks/1 HTTP/1.1
If-None-Match: "2"
```

Response

``` code
HTTP/1.1 304 
ETag: "2"
```

### Case 9: no such task

**Why:** `404`.

Request

``` code
GET /tasks/99 HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No such task",
  "instance": "/tasks/99",
  "status": 404,
  "title": "Not Found"
}
```

## The activity feed afterwards

From `psql` in `docs/capture.sh`: one row per accepted change, none for the refused ones.

``` code
 task_id | version |          title          | status 
---------+---------+-------------------------+--------
       1 |       1 | Write the press release | doing
       1 |       2 | Write the press release | doing
(2 rows)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                        | What happens                                | Proved by                                         |
|---------------------------------------------|---------------------------------------------|---------------------------------------------------|
| A read                                      | The task with `ETag: "0"`                   | `aTaskComesWithItsVersionAsETag`                  |
| A save with the ETag                        | `200`, the next ETag, the title trimmed     | `anEditWithTheETagSavesAndGivesTheNextETag`       |
| Polling with the current ETag               | `304`; after a change, `200`                | `anUnchangedTaskIs304ForAPollingBoard`            |
| Unknown task                                | `404`                                       | `anUnknownTaskIs404`                              |
| No If-Match                                 | `428`                                       | `anEditWithoutIfMatchIs428`                       |
| A title already on the board                | `409`, version unchanged                    | `aTitleAlreadyOnTheBoardIs409NotA412`             |
| Bad bodies                                  | `400`                                       | `badBodiesAre400`                                 |
| Ten saves of one version at once            | One `200`, nine `412`, one activity row     | `tenEditsOfTheSameVersionAtOnceSaveExactlyOne`    |
| Ten editors that read, edit, retry          | All ten changes land, version 10            | `editsThatEachReadFirstAllLandInTurn`             |
| An UPDATE without the version, in plain SQL | Refused by the trigger                      | `anUpdateThatForgetsTheVersionIsRefused`          |
| Other rules in plain SQL                    | Refused by named constraints                | `taskRulesHoldWithoutJava`                        |
| A save whose activity row fails             | Rolled back; the same edit works afterwards | `anEditWhoseActivityRowFailsLeavesTheTaskAsItWas` |

## The trap

Plausible but wrong

Last write wins: two editors silently overwrite each other.

- **The old board.** Meera and Kabir open the card; Meera saves "doing"; Kabir saves his screen, which still says "open". The card ends with Kabir's assignee and the old status: Meera's change is gone, and nobody was told.
- **The API.** The same two saves: Meera's with `"0"` is saved; Kabir's with `"0"` is `412`. He reads again and saves on top: both changes are kept.

While building, each part was undone once: no `@Version` turned 6 tests red (every edit then failed on the version trigger); saving on the current version instead of the one in `If-Match` 2; the save without its transaction 1; no `428` 1; no version trigger 1.

``` code
package com.taskloom.board;

import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old board saved whatever the editor sent: last write wins. Two managers open the same card;
 * one moves it to "doing", the other reassigns it, both press Save. Each test runs the old way, then the API.
 */
class LastWriteWinsTrapTest extends ApiTest {

    /** The old save, as it was: the whole card from the editor's screen replaces the stored one. */
    static final class OldBoard {
        final Map<String, String> card = new HashMap<>(Map.of("status", "open", "assignee", "asha"));

        Map<String, String> open() {
            return new HashMap<>(card);
        }

        void save(Map<String, String> screen) {
            card.putAll(screen);
        }
    }

    @Test
    void theOldBoardSilentlyDroppedOneManagersChange() {
        OldBoard old = new OldBoard();
        Map<String, String> meera = old.open();
        Map<String, String> kabir = old.open();
        meera.put("status", "doing");
        old.save(meera);
        kabir.put("assignee", "ravi");
        old.save(kabir);   // kabir's screen still says "open"
        assertThat(old.card).containsEntry("assignee", "ravi").containsEntry("status", "open");   // meera's change is gone, and nobody was told
    }

    @Test
    void theSecondSaveOnTheSameVersionIsRefusedAndNothingIsLost() throws Exception {
        String bothRead = etag(1);
        edit(1, bothRead, body("Write the press release", "doing", "asha")).andExpect(status().isOk());       // meera
        edit(1, bothRead, body("Write the press release", "open", "ravi")).andExpect(status().isPreconditionFailed())   // kabir, from the old copy
                .andExpect(jsonPath("$.detail").value("Someone changed this task after you read it. Read it again, then edit."));
        read(1).andExpect(jsonPath("$.status").value("doing")).andExpect(jsonPath("$.assignee").value("asha"));
        // kabir reads again, sees meera's change, and makes his on top of it.
        edit(1, etag(1), body("Write the press release", "doing", "ravi")).andExpect(status().isOk()).andExpect(header().string("ETag", "\"2\""));
        read(1).andExpect(jsonPath("$.status").value("doing")).andExpect(jsonPath("$.assignee").value("ravi"));
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
./mvnw test                 # all 14 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Two saves from the same read:

``` code
for who in meera kabir; do
  curl -s -o /dev/null -w "$who %{http_code}\n" -X PUT http://localhost:8080/tasks/2 -H 'Content-Type: application/json' -H 'If-Match: "0"' \
    -d "{\"title\": \"Book the venue\", \"description\": \"Capacity 200.\", \"status\": \"done\", \"assignee\": \"$who\"}"
done
```

It prints `meera 200` and `kabir 412`.

## Troubleshooting

| You see                                        | Cause                                                                   | Fix                                                                         |
|------------------------------------------------|-------------------------------------------------------------------------|-----------------------------------------------------------------------------|
| `tasks_version_must_increase: version 0 to 0`  | A writer updated without moving the version (here: `@Version` removed). | Let `@Version` do it, or write `version = version + 1 ... AND version = ?`. |
| `A result was returned when none was expected` | A `SELECT` run through `update()`.                                      | Use a statement that returns nothing, as V2 does.                           |
| Every save is `412`                            | The client sends a weak ETag (`W/"1"`).                                 | Send the ETag exactly as received; `If-Match` compares strongly.            |
| `Could not find a valid Docker environment`    | Docker is not running.                                                  | Start Docker Desktop or the Docker service.                                 |

## Project layout

``` tree
stations/080-task-board-edits-without-lost-updates/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/taskloom/board/
│   ├── TaskController.java   ├── TaskEdits.java   ├── Task.java
│   ├── Tasks.java   └── BoardApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__tasks.sql, V2__demo_board.sql
├── src/test/java/com/taskloom/board/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/taskloom/board/TaskController.java`

Does  
Read with an ETag; save only with If-Match.

Why  
No `If-Match` is `428`; a value that is not one of our strong ETags is `412`; the response carries the next ETag.

Without it  
Saves that do not say what they are based on.

Spring MVC answers `If-None-Match` by itself for a `ResponseEntity` that carries an ETag: the `304` in case 8 needs no code here. Found while building, when a planned challenge passed with nothing written.

#### `src/main/java/com/taskloom/board/TaskEdits.java`

Does  
The save.

Why  
`@Version` makes it one `UPDATE ... AND version = ?`; no row is `412`; a title clash is `409`; the activity row in the same transaction.

Without it  
Two saves of one version both winning, or a feed that lists changes that never happened.

Spring Data JDBC throws `OptimisticLockingFailureException` and `DuplicateKeyException` as they are, not wrapped. A first version walked the cause chain; removing the walk changed no test, so it is two catch clauses now.

#### `src/main/java/com/taskloom/board/Task.java`

The card as a record; `@Version` on the version.

#### `src/main/java/com/taskloom/board/Tasks.java`

A Spring Data repository.

#### `src/main/resources/db/migration/V1__tasks.sql`

Does  
Tasks, the activity feed, and the version trigger.

Why  
Every UPDATE must move the version on by exactly one, from any writer.

Without it  
A script or an old service writing without a version, the way the old board did.

A CHECK cannot compare the old and new row, so this rule is a trigger that raises a `check_violation` named after it.

#### `src/main/resources/db/migration/V2__demo_board.sql`

Two demo tasks. `ALTER ... RESTART WITH 3` instead of `SELECT setval(...)`, because the tests reload this file and `update()` refuses a statement that returns a row.

#### `src/main/resources/application.yaml`

The database connection.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/taskloom/board/BoardApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                             | Test class                  | Result |
|---------------|---------------------------------------------------------|-----------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                | `TaskContractTest` (7)      | pass   |
| Every station | Reproduce the failure before the fix                    | `LastWriteWinsTrapTest` (2) | pass   |
| Database      | Rollback and constraint tests against a real database   | `TaskDatabaseTest` (3)      | pass   |
| Concurrency   | A real concurrency test that proves the invariant holds | `TaskConcurrencyTest` (2)   | pass   |

The parallel tests run on virtual threads released together by one latch, against the real PostgreSQL. The invariant: one saved change per version, and the activity feed agrees with the task.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, Spring Data JDBC, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.board.LastWriteWinsTrapTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.board.TaskConcurrencyTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.board.TaskDatabaseTest
[INFO] Tests run: 7, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.board.TaskContractTest
[INFO] Tests run: 14, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/taskloom/board/LastWriteWinsTrapTest.java`

Written first: the old board drops a change; the API refuses the stale save and keeps both.

#### `src/test/java/com/taskloom/board/TaskConcurrencyTest.java`

Ten saves of one version at once; ten editors that read, edit and retry.

#### `src/test/java/com/taskloom/board/TaskDatabaseTest.java`

The version trigger and every named constraint with plain SQL; a save whose activity row fails.

#### `src/test/java/com/taskloom/board/TaskContractTest.java`

ETags, 304, 404, 428, 409, 400 through HTTP.

#### `src/test/java/com/taskloom/board/ApiTest.java`

Shared setup: the demo board from V2 before each test, request helpers.

#### `src/test/java/com/taskloom/board/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/taskloom/board/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=PatchChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 14 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 18 tests pass (14 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 30 minutes

## PATCH only what changed

`PATCH /tasks/{id}` with a JSON merge patch (`application/merge-patch+json`) changes only the fields sent, with the same `If-Match` rules as PUT.

**Done when:** both tests in `PatchChallengeTest` pass.

Hints

- Merge the fields sent into the stored task, validate the result like a PUT body, then save it the same way.
- A PATCH changes less, but it is still based on a version: `If-Match` stays required.

#### `challenge/PatchChallengeTest.java`

``` code
package com.taskloom.board;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: PATCH /tasks/{id} with a JSON merge patch (application/merge-patch+json, RFC 7396) changes only the
 * fields sent. The same rules as PUT: If-Match required (428), an old ETag is 412.
 */
class PatchChallengeTest extends ApiTest {

    @Test
    void onlyTheFieldsSentChange() throws Exception {
        mvc.perform(patch("/tasks/1").header("If-Match", etag(1)).contentType(MediaType.valueOf("application/merge-patch+json")).content("{\"status\":\"done\"}"))
                .andExpect(status().isOk()).andExpect(header().string("ETag", "\"1\""))
                .andExpect(jsonPath("$.status").value("done")).andExpect(jsonPath("$.assignee").value("asha")).andExpect(jsonPath("$.title").value("Write the press release"));
    }

    @Test
    void theSameRulesAsPut() throws Exception {
        mvc.perform(patch("/tasks/1").contentType(MediaType.valueOf("application/merge-patch+json")).content("{\"status\":\"done\"}")).andExpect(status().isPreconditionRequired());
        mvc.perform(patch("/tasks/1").header("If-Match", "\"7\"").contentType(MediaType.valueOf("application/merge-patch+json")).content("{\"status\":\"done\"}")).andExpect(status().isPreconditionFailed());
        mvc.perform(patch("/tasks/1").header("If-Match", "\"0\"").contentType(MediaType.valueOf("application/merge-patch+json")).content("{\"status\":\"blocked\"}")).andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 20 minutes

## Delete only what you saw

`DELETE /tasks/{id}` with `If-Match`: `204` if the task is still that version, `412` if it changed since, `428` without the header.

**Done when:** both tests in `ConditionalDeleteChallengeTest` pass.

Hints

- With `@Version`, Spring Data JDBC deletes with `AND version = ?` too.
- Pass the version from `If-Match`, not the one you just read.

#### `challenge/ConditionalDeleteChallengeTest.java`

``` code
package com.taskloom.board;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: DELETE /tasks/{id} with If-Match: 204 if the task is still the version you saw, 412 if someone changed
 * it since (you may be deleting their note), 428 without If-Match.
 */
class ConditionalDeleteChallengeTest extends ApiTest {

    @Test
    void deleteTheVersionYouSaw() throws Exception {
        mvc.perform(delete("/tasks/2").header("If-Match", etag(2))).andExpect(status().isNoContent());
        read(2).andExpect(status().isNotFound());
    }

    @Test
    void notAVersionSomeoneHasChangedSince() throws Exception {
        String seen = etag(1);
        edit(1, seen, body("Write the press release", "doing", "asha"));
        mvc.perform(delete("/tasks/1").header("If-Match", seen)).andExpect(status().isPreconditionFailed());
        mvc.perform(delete("/tasks/1")).andExpect(status().isPreconditionRequired());
        read(1).andExpect(status().isOk());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Merge instead of refuse

Meera changed the status and Kabir the assignee: the two edits do not touch the same field. Design a save that merges them automatically (keep the version each field was last changed at), and decide what happens when both change the same field. When would you need live collaboration instead (operational transform, CRDTs)?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: two saves from one read.
2.  A version column, `@Version`, and the version as the ETag.
3.  `If-Match` required; 412, 409 and 428 chosen on purpose.
4.  A trigger so no writer can skip the version.

## Design alternatives and trade-offs

| Approach                                               | What it costs                              | Verdict                       |
|--------------------------------------------------------|--------------------------------------------|-------------------------------|
| Optimistic: version in If-Match, checked in the UPDATE | The loser reads again.                     | Chosen                        |
| Last write wins                                        | Changes vanish silently.                   | The trap                      |
| Read the version, compare in Java, then update         | Two editors can pass the check together.   | A race                        |
| Pessimistic lock while editing (SELECT ... FOR UPDATE) | A row held for as long as someone edits.   | For seconds, never for a form |
| Merge field by field                                   | Per-field versions and a rule for clashes. | Kinder; more to build         |

## Database design

| Object                                                  | What    | Why                                       |
|---------------------------------------------------------|---------|-------------------------------------------|
| `tasks_version_must_increase`                           | Trigger | Every writer moves the version on by one. |
| `tasks_board_title_unique`                              | UNIQUE  | The rule behind the 409.                  |
| `tasks_status`, `_title_length`, `_version_nonnegative` | CHECKs  | Values the board can show.                |
| `task_changes_one_per_version`                          | UNIQUE  | One feed entry per accepted change.       |

**Transaction boundary:** one save is one transaction: the task and its activity row.

``` code
CREATE TABLE tasks (
    id          bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT tasks_pk PRIMARY KEY,
    board       text NOT NULL,
    title       text NOT NULL,
    description text NOT NULL,
    status      text NOT NULL,
    assignee    text,
    -- Counts every change. Every update must name the version it was based on; the ETag is this number.
    version     bigint NOT NULL DEFAULT 0,
    CONSTRAINT tasks_status CHECK (status IN ('open', 'doing', 'done')),
    CONSTRAINT tasks_title_length CHECK (char_length(title) BETWEEN 1 AND 120),
    CONSTRAINT tasks_version_nonnegative CHECK (version >= 0),
    -- Two cards with the same title on one board confuse everyone: a business rule, so a 409 when broken.
    CONSTRAINT tasks_board_title_unique UNIQUE (board, title)
);

-- The board's activity feed: one row per accepted change, written in the same transaction.
CREATE TABLE task_changes (
    id      bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT task_changes_pk PRIMARY KEY,
    task_id bigint NOT NULL CONSTRAINT task_changes_task_fk REFERENCES tasks ON DELETE CASCADE,
    version bigint NOT NULL,
    title   text NOT NULL,
    status  text NOT NULL,
    CONSTRAINT task_changes_one_per_version UNIQUE (task_id, version)
);

-- Every writer, not only this app, must move the version on by exactly one: an UPDATE that forgets it (the old
-- last-write-wins code) is refused. A CHECK cannot compare old and new rows, so this rule is a trigger.
CREATE FUNCTION tasks_version_must_increase() RETURNS trigger AS $$
BEGIN
    IF NEW.version <> OLD.version + 1 THEN
        RAISE EXCEPTION 'tasks_version_must_increase: version % to % on task %', OLD.version, NEW.version, OLD.id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER tasks_version_must_increase BEFORE UPDATE ON tasks FOR EACH ROW EXECUTE FUNCTION tasks_version_must_increase();
```

# 3 · Go deeper: Production

The second editor  
A `412` is only kind if the app shows what changed and keeps the user's text. Return or refetch the current task.

Caches and proxies  
ETags work with caches; make sure a proxy does not turn strong ETags into weak ones (some do when compressing), or every save fails.

Every writer  
Batch jobs and admin scripts are writers too: the trigger stops them from overwriting silently.

Standards  
ETag, If-Match, If-None-Match, 304 and 412 are in RFC 9110 and RFC 9111 (Internet Standards); 428 is RFC 6585 (Proposed Standard); JSON merge patch is RFC 7396 (Proposed Standard).

# 3 · Go deeper: Interview

## Interview takeaways

What is a lost update?

Two read-modify-write cycles overlap; the second write is based on old data and replaces the first change without anyone knowing.

How does @Version prevent it?

The update includes AND version = :expected and increments it. If another write got there first, no row matches and the save fails.

409 or 412?

412 when a precondition in the request (If-Match) is false: your copy is old. 409 when the request is current but conflicts with the resource's rules.

Why require If-Match (428)?

Without it the server cannot know which version the client edited, so it cannot tell a stale save from a fresh one.

Why not compare versions in Java first?

Two requests can both read version 3 and pass the check before either writes. The check must be in the same statement as the write.

## Self-check rubric

| Area        | Meets the bar          | Above the bar                                          |
|-------------|------------------------|--------------------------------------------------------|
| Correctness | All 14 tests pass.     | You ran the flawed version and explained each failure. |
| Versioning  | @Version and ETags.    | A database rule so no writer skips the version.        |
| HTTP        | 412 for stale saves.   | 409, 412 and 428 each where they belong.               |
| Proof       | A test with two saves. | Ten in parallel, and ten polite retries.               |

# 3 · Go deeper: Review

## The pull request

A teammate answers two complaints: editors dislike "read it again" errors, so saves now apply on top of the latest version; and the mobile app does not send `If-Match` yet, so it is optional. "`@Version` still guards the write." Read the two files and list every problem before opening the findings.

#### `review/TaskEdits.java`

``` code
package com.taskloom.board;

import org.springframework.dao.DuplicateKeyException;
import org.springframework.dao.OptimisticLockingFailureException;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
class TaskEdits {

    record Edit(String title, String description, String status, String assignee) {
    }

    private final Tasks tasks;
    private final JdbcClient jdbc;

    TaskEdits(Tasks tasks, JdbcClient jdbc) {
        this.tasks = tasks;
        this.jdbc = jdbc;
    }

    Task get(long id) {
        return tasks.findById(id).orElseThrow(TaskEdits::notFound);
    }

    /**
     * Saves the edit on top of the latest version, so editors no longer get "read it again" errors. @Version still
     * guards the write itself. The change and its activity row are one transaction.
     */
    @Transactional
    Task update(long id, long basedOn, Edit edit) {
        Task current = get(id);
        Task saved;
        try {
            saved = tasks.save(new Task(id, current.board(), edit.title().strip(), edit.description(), edit.status(), edit.assignee(), current.version()));
        } catch (OptimisticLockingFailureException stale) {
            // 412: the editor's copy is old. Read again, then edit.
            throw new ResponseStatusException(HttpStatus.PRECONDITION_FAILED, "Someone changed this task after you read it. Read it again, then edit.");
        } catch (DuplicateKeyException clash) {
            // 409: the copy is current, but the edit breaks a rule of the board.
            throw new ResponseStatusException(HttpStatus.CONFLICT, "A task with this title is already on the board");
        }
        jdbc.sql("INSERT INTO task_changes (task_id, version, title, status) VALUES (?, ?, ?, ?)")
                .params(saved.id(), saved.version(), saved.title(), saved.status()).update();
        return saved;
    }

    static ResponseStatusException notFound() {
        return new ResponseStatusException(HttpStatus.NOT_FOUND, "No such task");
    }
}
```

#### `review/TaskController.java`

``` code
package com.taskloom.board;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.util.regex.Matcher;

@RestController
class TaskController {

    record TaskBody(@NotBlank @Size(max = 120) String title, @NotNull @Size(max = 2000) String description,
                    @NotNull @Pattern(regexp = "open|doing|done") String status, @Size(max = 40) String assignee) {
    }

    /** A strong ETag holding the version, e.g. "3". shortcut: one ETag only, no lists and no *, which nobody here sends. */
    private static final java.util.regex.Pattern STRONG_ETAG = java.util.regex.Pattern.compile("\"(\\d{1,18})\"");

    private final TaskEdits edits;

    TaskController(TaskEdits edits) {
        this.edits = edits;
    }

    @GetMapping("/tasks/{id}")
    ResponseEntity<Task> get(@PathVariable long id) {
        Task task = edits.get(id);
        return ResponseEntity.ok().eTag(etag(task)).body(task);
    }

    /** Full replacement. If-Match is optional for now. */
    @PutMapping("/tasks/{id}")
    ResponseEntity<Task> put(@PathVariable long id, @RequestHeader(value = "If-Match", required = false) String ifMatch,
                             @Valid @RequestBody TaskBody body) {
        if (ifMatch == null) {
            ifMatch = "\"0\"";   // the mobile app does not send If-Match yet; the version is not used for saving anyway
        }
        Matcher m = STRONG_ETAG.matcher(ifMatch.strip());
        if (!m.matches()) {
            throw new ResponseStatusException(HttpStatus.PRECONDITION_FAILED, "If-Match must be the ETag from GET /tasks/" + id);
        }
        Task saved = edits.update(id, Long.parseLong(m.group(1)), new TaskEdits.Edit(body.title(), body.description(), body.status(), body.assignee()));
        return ResponseEntity.ok().eTag(etag(saved)).body(saved);
    }

    private static String etag(Task task) {
        return "\"" + task.version() + "\"";
    }
}
```

## Findings

1Saving on top of the latest version

"No more read it again errors": the save now uses the version it just read, not the one the editor saw. Every stale save succeeds and replaces the newer one: last write wins, with `@Version` still in the code.

**Test evidence:** `theSecondSaveOnTheSameVersionIsRefusedAndNothingIsLost` and `tenEditsOfTheSameVersionAtOnceSaveExactlyOne` fail.

2If-Match made optional

Clients that send nothing are treated as editing version 0, so they can never prove what they edited; with the first flaw, it would not matter anyway.

**Test evidence:** `anEditWithoutIfMatchIs428` fails.

## Same tests, flawed version

From `docs/review-run.txt`: the two flawed files copied over the real ones, then the full suite run.

| Test class              | Fixed version | Flawed version |
|-------------------------|---------------|----------------|
| `TaskDatabaseTest`      | 3 / 3         | 3 / 3          |
| `LastWriteWinsTrapTest` | 2 / 2         | 1 / 2          |
| `TaskConcurrencyTest`   | 2 / 2         | 1 / 2          |
| `TaskContractTest`      | 7 / 7         | 6 / 7          |

`@Version` "still guards the write" is true, and useless: it now guards against a race of milliseconds inside the server, while the real race, minutes between a read and a save, is let through.
