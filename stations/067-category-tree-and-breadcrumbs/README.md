# Station 067 · Category tree and breadcrumbs

Working Systems · 0–2 years · Core · E-commerce · Types: Database

Spring Boot 4.1.1 · Java 25 · JdbcClient · PostgreSQL 17 WITH RECURSIVE (SEARCH, CYCLE) · adjacency list · trigger with an advisory lock · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The category tree is demo data, not Kartwala's. No products are listed.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 10 tests.

# 1 · Understand

## The problem in real life

1.  **A product page**

    Shows "Home \> Electronics \> Phones \> Android". The code asked for Android, then its parent, then that one's parent: four queries, one per level.

2.  **A loop**

    An admin moved Electronics under Phones. Now Phones is under Electronics under Phones… The breadcrumb code followed parents forever, and the page never loaded.

3.  **The fix**

    One recursive query walks the tree inside PostgreSQL, and stops if it ever meets a category twice. And the database refuses any move that would make a loop.

Walk a tree in one query, and never let it stop being a tree.

## What are we building?

`GET /categories/4/breadcrumb` gives the path from Home to Android; `GET /categories/8/descendants` gives everything under Fashion, as an indented menu.

## An everyday analogy

A family where each person only knows their mother. To find your great-grandmother, you could phone your mother, who phones hers, and so on: one call per generation. Or you hand the whole family register to someone who reads it all at once.

## How it works in 4 steps

1.  **Start** at the category asked for.
2.  **Repeat**: join each found row to its parent (breadcrumb) or its children (descendants).
3.  **Stop** when there is nothing more, or if a category comes round a second time.
4.  **Order**: root first for breadcrumbs; depth first, by name, for menus.

Check yourself: Phones moves from Electronics to Home. How many rows change with this design? With a stored path on every row?

Here, one: Phones' `parent_id`. Every breadcrumb under it follows automatically. With a materialised path, Phones and every category under it must be rewritten, and any link built from the old path breaks.

## What this station is not

- **No products.** Only the tree.
- **No admin screens.** Moving is Practice 2.
- **No caching.** Menus change rarely and cache well; that comes later.

## Key terms

| Term                  | Simple meaning                                                      | Everyday example                                          | In this project                  |
|-----------------------|---------------------------------------------------------------------|-----------------------------------------------------------|----------------------------------|
| **Tree**              | Each category has at most one parent; one category, Home, has none. | A family tree, or folders on a computer.                  | `categories`                     |
| **Adjacency list**    | Each row stores only its parent's id.                               | Each person knows only their own mother.                  | `parent_id`                      |
| **Breadcrumb**        | The path from the top to where you are.                             | Home \> Electronics \> Phones \> Android.                 | `/breadcrumb`                    |
| **Recursive query**   | A query that repeats a step until there is nothing left.            | "Ask your mother who her mother was", until no one knows. | `WITH RECURSIVE`                 |
| **Cycle**             | A category that is, through its parents, under itself.              | A folder inside its own subfolder.                        | refused by `categories_no_cycle` |
| **Materialised path** | Each row stores its whole path as text.                             | Writing your full address on everything you own.          | the alternative in Design        |

# 2 · Build: Spec

## Business problem

**Kartwala** (a fictional marketplace) took 4 queries per product page for its breadcrumb, and a category move created a loop that hung the page.

## Acceptance criteria

Demo data: Home with Electronics and Fashion, and a Hobbies branch 12 levels deep.

1.  **Given** Android, **then** "Home \> Electronics \> Phones \> Android".
2.  **Given** Fashion, **then** Men, Shoes, Women, Sarees, Shoes, with depths 1, 2, 1, 2, 2.
3.  **Given** any depth, **then** one SQL statement.
4.  **Given** a leaf, **then** no descendants; an unknown id, `404`; a non-number, `400`.
5.  **Given** a move under its own descendant, by anyone, **then** the database refuses it.

## Requirements

- Store only the parent; derive paths when asked.
- Every recursive query has a `CYCLE` guard.
- The database refuses cycles, self-parents, duplicate slugs under one parent, and a second root with the same slug.
- Moves take turns, so two moves at once cannot build a loop between them.

## Learning objectives

- Model a tree as an adjacency list.
- Write `WITH RECURSIVE` up and down a tree, with `SEARCH` and `CYCLE`.
- Prevent cycles in the database.
- Compare adjacency list, materialised path and closure table.

# 2 · Build: API contract

## Endpoints

| Method | Path                           | Purpose                                                                                  |
|--------|--------------------------------|------------------------------------------------------------------------------------------|
| `GET`  | `/categories/{id}/breadcrumb`  | `{id, path, trail: [{id, name, slug}]}`, Home first.                                     |
| `GET`  | `/categories/{id}/descendants` | `{id, descendants: [{id, parentId, name, slug, depth}]}`, depth first, siblings by name. |

## Status codes

| Status | When                                   |
|--------|----------------------------------------|
| 200    | A breadcrumb or a list, possibly empty |
| 400    | The id is not a number                 |
| 404    | No such category                       |

## Captured examples

Captured with curl from the running app on 16 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: Android's breadcrumb

**Why:** four levels, one query.

Request

``` code
GET /categories/4/breadcrumb HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 237

{
  "id": 4,
  "path": "Home > Electronics > Phones > Android",
  "trail": [
    {
      "id": 1,
      "name": "Home",
      "slug": "home"
    },
    {
      "id": 2,
      "name": "Electronics",
      "slug": "electronics"
    },
    {
      "id": 3,
      "name": "Phones",
      "slug": "phones"
    },
    {
      "id": 4,
      "name": "Android",
      "slug": "android"
    }
  ]
}
```

### Case 2: everything under Fashion

**Why:** depth first, siblings by name; two categories called Shoes, under different parents.

Request

``` code
GET /categories/8/descendants HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 338

{
  "id": 8,
  "descendants": [
    {
      "id": 9,
      "parentId": 8,
      "name": "Men",
      "slug": "men",
      "depth": 1
    },
    {
      "id": 10,
      "parentId": 9,
      "name": "Shoes",
      "slug": "shoes",
      "depth": 2
    },
    {
      "id": 11,
      "parentId": 8,
      "name": "Women",
      "slug": "women",
      "depth": 1
    },
    {
      "id": 12,
      "parentId": 11,
      "name": "Sarees",
      "slug": "sarees",
      "depth": 2
    },
    {
      "id": 13,
      "parentId": 11,
      "name": "Shoes",
      "slug": "shoes",
      "depth": 2
    }
  ]
}
```

### Case 3: iPhone's descendants

**Why:** a leaf: an empty list.

Request

``` code
GET /categories/5/descendants HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 25

{
  "id": 5,
  "descendants": []
}
```

### Case 4: category 999

**Why:** `404`.

Request

``` code
GET /categories/999/breadcrumb HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No category 999",
  "instance": "/categories/999/breadcrumb",
  "status": 404,
  "title": "Not Found"
}
```

## The move that made the loop, tried on the real table

From `docs/capture.sh`, in `psql` (`docs/captures/loop-refused.txt`).

``` code
ERROR:  categories_no_cycle: category 2 cannot move under its own descendant 3
CONTEXT:  PL/pgSQL function categories_no_cycle() line 10 at RAISE
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                       | What happens                              | Proved by                                     |
|------------------------------------------------------------|-------------------------------------------|-----------------------------------------------|
| Root, 4 levels, 14 levels                                  | Correct trail, one statement              | `theBreadcrumbRunsFromHomeToTheCategory`      |
| A branch with same-named children                          | Menu order, depths, parents               | `descendantsReadLikeAnIndentedMenu`           |
| A leaf                                                     | Empty list                                | `aLeafHasNoDescendants`                       |
| Unknown id; not a number                                   | `404`; `400`                              | `anUnknownCategoryIs404AndANonNumberIs400`    |
| A loop in old data                                         | Old loop: endless; recursive query: stops | `aLoopInTheOldDataKeptTheOldCodeGoingForever` |
| The loop-making move today                                 | Refused by the trigger                    | `theRealTableRefusesTheMoveThatMadeTheLoop`   |
| Self-parent, duplicate slug, orphan, bad slug, second Home | Refused by named constraints              | `namedConstraintsHoldWithoutJava`             |
| A move; a half-added branch                                | One update; rolled back                   | `CategoryDatabaseTest`                        |

## The trap

Plausible but wrong

One query per level, and no protection against cycles.

The old loop is kept in the tests as `OldBreadcrumb`. On the real tree it sends 4 queries for Android and 14 for the deepest Hobbies level; the recursive query is one statement for both.

On a copy of the table without the cycle check, the test makes the admin's move: Electronics under Phones. The old loop follows parents round and round, and stops only at the test's own limit of 1,000 queries. The recursive query's `CYCLE` clause notices Phones the second time and stops after 3 rows. On the real table, the same `UPDATE` is refused.

While building, each fix was undone once: without the trigger, the trap test's move really created the loop in the shared table, and 2 contract tests failed after it, 3 red in all: the damage outlives the request that caused it. Ordering the trail root last turned 4 red; dropping the `SEARCH` clause 1; including the category in its own descendants 2; a plain `UNIQUE` (which treats every `NULL` parent as different, allowing a second Home) 1. Removing `CYCLE` was not tried: on a loop, the query never ends.

``` code
package com.kartwala.categories;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.catchThrowable;

/** Written first. The old loop, on the real tree and on an old copy of it without the cycle check. */
class QueryPerLevelTrapTest extends ApiTest {

    @Autowired
    CategoryTree tree;

    @AfterEach
    void dropOldCopy() {
        jdbc.sql("DROP TABLE IF EXISTS old_categories").update();
    }

    @Test
    void theOldLoopSendsOneQueryPerLevel() {
        OldBreadcrumb old = new OldBreadcrumb(jdbc, "categories");
        assertThat(old.breadcrumb(4, 1000)).containsExactly("Home", "Electronics", "Phones", "Android");
        assertThat(old.queries).isEqualTo(4);
        old.queries = 0;
        old.breadcrumb(112, 1000);
        assertThat(old.queries).isEqualTo(14);   // the new one: always 1 statement, WITH RECURSIVE
        assertThat(tree.breadcrumb(112).trail()).hasSize(14);
    }

    @Test
    void aLoopInTheOldDataKeptTheOldCodeGoingForever() {
        // The old table had no cycle check; an admin moved Electronics under Phones.
        jdbc.sql("CREATE TABLE old_categories AS SELECT id, parent_id, name, slug FROM categories").update();
        jdbc.sql("UPDATE old_categories SET parent_id = 3 WHERE id = 2").update();
        OldBreadcrumb old = new OldBreadcrumb(jdbc, "old_categories");
        old.breadcrumb(4, 1000);
        assertThat(old.queries).isEqualTo(1000);   // stopped only by the test's own limit

        // The recursive query's CYCLE clause stops at the first repeat: Android, Phones, Electronics, then Phones again.
        assertThat(jdbc.sql(CategoryTree.UP.replace("FROM categories", "FROM old_categories"))
                .param("id", 4).query((rs, i) -> rs.getString("name")).list()).containsExactly("Electronics", "Phones", "Android");
    }

    @Test
    void theRealTableRefusesTheMoveThatMadeTheLoop() {
        assertThat(catchThrowable(() -> jdbc.sql("UPDATE categories SET parent_id = 3 WHERE id = 2").update()))
                .hasMessageContaining("categories_no_cycle: category 2 cannot move under its own descendant 3");
        assertThat(tree.breadcrumb(4).path()).isEqualTo("Home > Electronics > Phones > Android");
    }
}
```

``` code
package com.kartwala.categories;

import org.springframework.jdbc.core.simple.JdbcClient;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/** The breadcrumb as it was, kept in the tests only: one query per level, walking up until there is no parent. */
class OldBreadcrumb {

    private final JdbcClient jdbc;
    private final String table;
    int queries;

    OldBreadcrumb(JdbcClient jdbc, String table) {
        this.jdbc = jdbc;
        this.table = table;
    }

    /** {@code stopAfter} is the test's own safety net; the old code had none. */
    List<String> breadcrumb(long id, int stopAfter) {
        List<String> names = new ArrayList<>();
        Long current = id;
        while (current != null && queries < stopAfter) {
            queries++;
            Map<String, Object> row = jdbc.sql("SELECT name, parent_id FROM " + table + " WHERE id = ?").param(current).query().singleRow();
            names.add((String) row.get("name"));
            current = (Long) row.get("parent_id");
        }
        Collections.reverse(names);
        return names;
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
./mvnw test                 # all 10 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Run the recursive query by hand and watch the `visited` path grow:

``` code
docker compose exec postgres psql -U kartwala -d kartwala
WITH RECURSIVE up (id, parent_id, name) AS (
    SELECT id, parent_id, name FROM categories WHERE id = 112
    UNION ALL SELECT c.id, c.parent_id, c.name FROM categories c JOIN up ON c.id = up.parent_id
) CYCLE id SET looped USING visited
SELECT name, visited FROM up;
```

## Troubleshooting

| You see                                                                  | Cause                                              | Fix                                                              |
|--------------------------------------------------------------------------|----------------------------------------------------|------------------------------------------------------------------|
| `categories_no_cycle: category … cannot move under its own descendant …` | A move would put a category inside itself.         | Expected; pick another parent.                                   |
| A recursive query that never returns                                     | A loop in the data and no `CYCLE` clause.          | Add `CYCLE id SET … USING …` (PostgreSQL 14+), or a depth limit. |
| `syntax error at or near "CYCLE"`                                        | PostgreSQL older than 14.                          | A `path` array column and `WHERE NOT id = ANY(path)`.            |
| Two Home categories accepted                                             | A plain `UNIQUE` treats every `NULL` as different. | `UNIQUE NULLS NOT DISTINCT` (PostgreSQL 15+).                    |

## Project layout

``` tree
stations/067-category-tree-and-breadcrumbs/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/categories/
│   ├── CategoryController.java   ├── CategoryTree.java   └── CategoriesApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__categories.sql, V2__demo_categories.sql
├── src/test/java/com/kartwala/categories/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/kartwala/categories/CategoryController.java`

Two endpoints; Spring answers a non-numeric id with `400`.

#### `src/main/java/com/kartwala/categories/CategoryTree.java`

Does  
The two recursive queries.

Why  
One statement per answer at any depth; `CYCLE` stops a loop; `SEARCH DEPTH FIRST` orders the menu.

Without it  
A query per level, and a loop that never ends.

- The first row of the descendants query is the category itself (depth 0), dropped before answering.
- `404` when the start row does not exist: the query returns nothing at all.

#### `src/main/resources/db/migration/V1__categories.sql`

Does  
The adjacency list, named constraints, and the cycle trigger.

Why  
The trigger walks up from the new parent; if it meets the category being moved, the move is a loop. The advisory lock makes moves take turns.

Without it  
A loop from any admin tool or script, not only this app.

#### `src/main/resources/db/migration/V2__demo_categories.sql`

13 categories and a 12-level Hobbies branch.

#### `src/main/resources/application.yaml`

Problem details on.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/kartwala/categories/CategoriesApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                  | Result |
|---------------|-------------------------------------------------------|-----------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found              | `CategoryContractTest` (4)  | pass   |
| Every station | Reproduce the failure before the fix                  | `QueryPerLevelTrapTest` (3) | pass   |
| Database      | Rollback and constraint tests against a real database | `CategoryDatabaseTest` (3)  | pass   |

Not tested: two moves at the same moment. The trigger's advisory lock makes them take turns, so the second sees the first's change; no parallel test proves it here.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.categories.CategoryDatabaseTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.categories.QueryPerLevelTrapTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.categories.CategoryContractTest
[INFO] Tests run: 10, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/kartwala/categories/QueryPerLevelTrapTest.java`

Written first: queries per level, the endless loop, and the refused move.

#### `src/test/java/com/kartwala/categories/CategoryDatabaseTest.java`

Named constraints, a one-row move, and a rolled-back branch.

#### `src/test/java/com/kartwala/categories/CategoryContractTest.java`

Both endpoints through HTTP.

#### `src/test/java/com/kartwala/categories/OldBreadcrumb.java`

The old loop, counting its own queries.

#### `src/test/java/com/kartwala/categories/ApiTest.java`

Shared setup.

#### `src/test/java/com/kartwala/categories/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/kartwala/categories/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=ChildrenChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 10 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 13 tests pass (10 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## One level of the menu

Add `GET /categories/{id}/children`: direct children by name, each with `hasChildren` for the menu's arrow.

**Done when:** the test in `ChildrenChallengeTest` passes.

Hints

- No recursion needed: `WHERE parent_id = ?`.
- `EXISTS (SELECT 1 … WHERE g.parent_id = c.id)` per row answers the arrow.

#### `challenge/ChildrenChallengeTest.java`

``` code
package com.kartwala.categories;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /categories/{id}/children lists the direct children by name, each with "hasChildren", so a menu
 * can show an arrow without loading the next level. Unknown category: 404.
 */
class ChildrenChallengeTest extends ApiTest {

    @Test
    void directChildrenWithAnArrowWhereThereIsMore() throws Exception {
        mvc.perform(get("/categories/2/children")).andExpect(status().isOk())
                .andExpect(jsonPath("$[*].name", contains("Laptops", "Phones")))
                .andExpect(jsonPath("$[*].hasChildren", contains(true, true)));
        mvc.perform(get("/categories/3/children")).andExpect(status().isOk())
                .andExpect(jsonPath("$[*].name", contains("Android", "iPhone"))).andExpect(jsonPath("$[*].hasChildren", contains(false, false)));
        mvc.perform(get("/categories/999/children")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Move a branch

Add `PUT /categories/{id}/parent` `{"parentId"}`: move the category and everything under it, answer its new breadcrumb. A loop is `409`; unknown ids `404`.

**Done when:** both tests in `MoveCategoryChallengeTest` pass.

Hints

- One `UPDATE`; the trigger decides about loops.
- The trigger raises a `check_violation`: Spring turns it into a `DataIntegrityViolationException`.

#### `challenge/MoveCategoryChallengeTest.java`

``` code
package com.kartwala.categories;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: PUT /categories/{id}/parent {"parentId": 2} moves a category with everything under it and answers its
 * new breadcrumb. A move under its own descendant is 409 (the database's categories_no_cycle refuses it); an unknown
 * category or parent is 404.
 */
class MoveCategoryChallengeTest extends ApiTest {

    @AfterEach
    void putPhonesBack() {
        jdbc.sql("UPDATE categories SET parent_id = 2 WHERE id = 3").update();
    }

    @Test
    void aMoveTakesTheWholeBranch() throws Exception {
        mvc.perform(put("/categories/3/parent").contentType(MediaType.APPLICATION_JSON).content("{\"parentId\": 1}")).andExpect(status().isOk())
                .andExpect(jsonPath("$.path").value("Home > Phones"));
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get("/categories/4/breadcrumb"))
                .andExpect(jsonPath("$.path").value("Home > Phones > Android"));
    }

    @Test
    void aLoopIs409AndUnknownIs404() throws Exception {
        mvc.perform(put("/categories/2/parent").contentType(MediaType.APPLICATION_JSON).content("{\"parentId\": 4}")).andExpect(status().isConflict());
        mvc.perform(put("/categories/2/parent").contentType(MediaType.APPLICATION_JSON).content("{\"parentId\": 999}")).andExpect(status().isNotFound());
        mvc.perform(put("/categories/999/parent").contentType(MediaType.APPLICATION_JSON).content("{\"parentId\": 1}")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Three ways to store a tree

Compare the adjacency list (here), a materialised path (`'/1/2/3/4/'`, or PostgreSQL's `ltree`), and a closure table (one row per ancestor–descendant pair) for: a breadcrumb, all descendants, moving Phones with 400 subcategories, and keeping product URLs working after the move. Which one makes "all products under Electronics" a plain index lookup?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: queries per level, and the loop.
2.  Keep the adjacency list; write the two recursive queries with `CYCLE`.
3.  Add the trigger that refuses loops, and make moves take turns.
4.  Name every constraint, and test each one with plain SQL.

## Design alternatives and trade-offs

| Approach                                        | What it costs                                         | Verdict                |
|-------------------------------------------------|-------------------------------------------------------|------------------------|
| Adjacency list + WITH RECURSIVE + cycle trigger | A recursive query per read.                           | Chosen                 |
| Adjacency list, one query per level in Java     | Queries grow with depth; loops never end.             | The trap               |
| Materialised path / `ltree`                     | Fast subtree reads; a move rewrites every row below.  | Read-heavy, rare moves |
| Closure table                                   | Fast everything; many rows; moves rewrite many pairs. | Large trees            |
| Nested sets (left/right numbers)                | Fast reads; inserts renumber half the tree.           | Rarely worth it        |

## Database design

| Object                       | What                                             | Why                                             |
|------------------------------|--------------------------------------------------|-------------------------------------------------|
| `categories_parent_fk`       | `parent_id` references `categories`              | No orphans.                                     |
| `categories_not_own_parent`  | CHECK                                            | The one-step loop, without the trigger.         |
| `categories_slug_per_parent` | UNIQUE NULLS NOT DISTINCT (parent_id, slug)      | Unique URLs per level, and one root per slug.   |
| `categories_no_cycle`        | Trigger before insert or a change of `parent_id` | Every longer loop, from any writer.             |
| `categories_parent`          | Index on `parent_id`                             | The descendants query joins children by parent. |

``` code
-- An adjacency list: each category names its parent. Moving a category is one UPDATE; nothing else stores its path.
CREATE TABLE categories (
    id        BIGINT       PRIMARY KEY,
    parent_id BIGINT       CONSTRAINT categories_parent_fk REFERENCES categories (id),
    name      VARCHAR(60)  NOT NULL,
    slug      VARCHAR(60)  NOT NULL CONSTRAINT categories_slug_shape CHECK (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
    CONSTRAINT categories_not_own_parent CHECK (parent_id <> id),
    CONSTRAINT categories_slug_per_parent UNIQUE NULLS NOT DISTINCT (parent_id, slug)
);
CREATE INDEX categories_parent ON categories (parent_id);

-- No category may sit under one of its own descendants: that would be a loop with no root.
-- The advisory lock makes moves take turns, so two moves at once cannot build a loop between them.
CREATE FUNCTION categories_no_cycle() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.parent_id IS NOT NULL THEN
        PERFORM pg_advisory_xact_lock(hashtext('categories_tree'));
        IF EXISTS (WITH RECURSIVE up AS (
                       SELECT id, parent_id FROM categories WHERE id = NEW.parent_id
                       UNION ALL
                       SELECT c.id, c.parent_id FROM categories c JOIN up ON c.id = up.parent_id)
                   SELECT 1 FROM up WHERE id = NEW.id) THEN
            RAISE EXCEPTION 'categories_no_cycle: category % cannot move under its own descendant %', NEW.id, NEW.parent_id
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER categories_no_cycle BEFORE INSERT OR UPDATE OF parent_id ON categories
    FOR EACH ROW EXECUTE FUNCTION categories_no_cycle();
```

# 3 · Go deeper: Production

URLs after a move  
Links built from slugs (`/electronics/phones`) change when Phones moves. Keep product URLs on ids, or redirect old paths.

Caching  
The whole tree is small and changes rarely: cache it and clear the cache on every move.

Big moves  
Moving is one row here, but anything derived from paths (search indexes, caches) must be rebuilt for the whole branch.

The advisory lock  
One lock for the whole tree: moves are rare, so taking turns costs nothing. With many concurrent moves, lock per branch instead.

# 3 · Go deeper: Interview

## Interview takeaways

How do you store a tree in a relational database?

Most simply as an adjacency list: each row has its parent's id. Alternatives are materialised paths, closure tables and nested sets.

How does WITH RECURSIVE work?

A starting query, UNION ALL, and a step that joins the previous rows to the table; PostgreSQL repeats the step until it returns no rows.

How do you stop a recursive query from looping?

The CYCLE clause (PostgreSQL 14+) tracks visited ids; or keep a path array and refuse ids already in it; or limit the depth.

How do you prevent cycles?

Before changing a parent, check that the new parent is not a descendant; do it in the database (a trigger) so every writer is checked, and serialise moves.

Why not store the full path?

Reads get simpler, but moving a category means rewriting it and everything under it, and any path-based link breaks.

## Self-check rubric

| Area        | Meets the bar                  | Above the bar                        |
|-------------|--------------------------------|--------------------------------------|
| Correctness | All 10 tests pass.             | You ran the recursive query by hand. |
| SQL         | WITH RECURSIVE up and down.    | SEARCH and CYCLE clauses.            |
| Integrity   | Loops refused by the database. | Why moves must take turns.           |
| Design      | Knows the adjacency list.      | Can argue for a closure table.       |

# 3 · Go deeper: Review

## No reviewer view for this station

This station has no flawed version to review. Use this checklist on any hierarchy:

- Does any loop in Java follow parents one query at a time?
- Does every recursive query have a cycle guard or a depth limit?
- Can any writer create a loop, or a second root?
- What breaks when a branch moves: URLs, caches, search?
