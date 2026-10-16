# Station 064 · Dish search with PostgreSQL full-text

Working Systems · 0–2 years · Core · Food delivery · Types: Database

Spring Boot 4.1.1 · Java 25 · JdbcClient · PostgreSQL 17 full-text search (tsvector, websearch_to_tsquery, ts_rank) · GIN index · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Dishes, restaurants and prices are demo data (200,008 rows), not Tiffino's. Nothing is ordered.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 13 tests.

# 1 · Understand

## The problem in real life

1.  **A hungry customer**

    Types "paneer tikka". The menu has "Paneer Tikka Masala".

2.  **Nothing found, slowly**

    The search compared characters: lower-case "paneer" is not "Paneer", "dosas" is not "Dosa", and descriptions were never looked at. And `LIKE '%…%'` reads every dish's name to find the few that match.

3.  **The fix**

    Store each dish's words, normalised, in a `tsvector` kept by PostgreSQL; search words with a GIN index; rank name matches first.

People search with words. Match words, not characters, and let an index find them.

## What are we building?

`GET /dishes/search?q=paneer tikka&city=pune`: up to 20 dishes that contain those words, best matches first.

## An everyday analogy

A cookbook's index. You look up "paneer" and get page numbers, instead of reading every recipe. The index lists "dosa" once for "dosa" and "dosas", and ignores "the" and "with".

## How it works in 4 steps

1.  **When a dish is saved**, PostgreSQL turns its name and description into words: "Paneer Tikka Masala" → paneer, tikka, masala.
2.  **When someone searches**, their text becomes words the same way: "TIKKAS paneer" → tikka AND paneer.
3.  **The GIN index** finds the dishes with all those words.
4.  **Ranking** puts dishes with the words in their name before those with them only in the description.

Check yourself: someone types "panner". What does full-text search return?

Nothing: "panner" is not a word in any dish, and full-text search does not guess spellings. That is a real limit, tested on purpose; Practice 2 adds "did you mean" with trigrams.

## What this station is not

- **No typo tolerance.** Practice 2; a search engine does it better.
- **No Hindi or Marathi.** One language configuration, English.
- **No ordering.** Dishes are read only.

## Key terms

| Term                 | Simple meaning                                               | Everyday example                                         | In this project                |
|----------------------|--------------------------------------------------------------|----------------------------------------------------------|--------------------------------|
| **Full-text search** | Searching by words, not by exact characters.                 | Asking a waiter for "something with paneer".             | this station                   |
| **tsvector**         | A row's text as a sorted list of normalised words (lexemes). | The index at the back of a cookbook.                     | the `search` column            |
| **tsquery**          | The words being searched for, with AND, OR, NOT.             | "Paneer and tikka, not Mysore."                          | `websearch_to_tsquery`         |
| **Stemming**         | Reducing words to a common root.                             | dosas, dosa → dosa.                                      | the `english` configuration    |
| **GIN index**        | For each word, the list of rows containing it.               | The cookbook index: paneer → pages 12, 40, 77.           | `dishes_search`                |
| **Ranking**          | Ordering matches by how well they match.                     | A dish named "Paneer Tikka" before one that mentions it. | `ts_rank` with weights A and B |

# 2 · Build: Spec

## Business problem

**Tiffino** (a fictional food delivery app) has 3 million dishes. Its search missed obvious matches and scanned every dish.

## Acceptance criteria

Demo data: 7 Pune dishes and 1 Mumbai dish written out, 200,000 generated ones that never mention paneer, tikka or dosa.

1.  **Given** "paneer tikka" in Pune, **then** the three dishes with both words in the name, then Butter Chicken, whose description mentions paneer tikka.
2.  **Given** "TIKKAS PANEER", **then** the same four; "dosas" finds both dosas.
3.  **Given** `"masala dosa" -mysore`, **then** only Masala Dosa.
4.  **Given** characters such as `& | ! ( :*`, **then** they are ignored, never a `500`.
5.  **Given** only stop words, a typo, or another city, **then** an empty list.
6.  **Given** q shorter than 2 or longer than 100, or no city, **then** `400`.

## Requirements

- The search vector is kept by the database (a generated column), never by app code.
- User text goes through `websearch_to_tsquery`, never `to_tsquery`.
- The search uses the GIN index; checked with EXPLAIN in a test.
- Name matches rank above description matches.

## Learning objectives

- Build a weighted `tsvector` as a generated column.
- Choose between `to_tsquery`, `plainto_tsquery` and `websearch_to_tsquery`.
- Index it with GIN and rank with `ts_rank`.
- Know what full-text search does not do.

# 2 · Build: API contract

## Endpoint

| Method | Path                        | Purpose                                                                            |
|--------|-----------------------------|------------------------------------------------------------------------------------|
| `GET`  | `/dishes/search?q=…&city=…` | `{q, city, dishes: [{id, name, restaurant, pricePaise}]}`, at most 20, best first. |

The search text understands what people already type into search boxes: words (all must match), `"exact phrase"`, `-word` to exclude, and `or`.

## Status codes

| Status | When                                                                           |
|--------|--------------------------------------------------------------------------------|
| 200    | Results, possibly an empty list                                                |
| 400    | q missing, under 2 or over 100 characters; city missing or not 3 to 30 letters |

## Captured examples

Captured with curl from the running app on 16 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: paneer tikka

**Why:** both words anywhere in the name or description; Butter Chicken last, a description match.

Request

``` code
POST /dishes/search HTTP/1.1

city=pune
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 383

{
  "q": "paneer tikka",
  "city": "pune",
  "dishes": [
    {
      "id": 4,
      "name": "Tandoori Paneer Tikka Roll",
      "restaurant": "Tandoor Express",
      "pricePaise": 18000
    },
    {
      "id": 1,
      "name": "Paneer Tikka Masala",
      "restaurant": "Punjab Grill",
      "pricePaise": 32000
    },
    {
      "id": 2,
      "name": "Paneer Tikka",
      "restaurant": "Punjab Grill",
      "pricePaise": 28000
    },
    {
      "id": 3,
      "name": "Butter Chicken",
      "restaurant": "Punjab Grill",
      "pricePaise": 34000
    }
  ]
}
```

### Case 2: DOSAS in Pune

**Why:** case and plural do not matter.

Request

``` code
POST /dishes/search HTTP/1.1

city=Pune
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 191

{
  "q": "DOSAS",
  "city": "pune",
  "dishes": [
    {
      "id": 5,
      "name": "Masala Dosa",
      "restaurant": "Vaishali",
      "pricePaise": 12000
    },
    {
      "id": 6,
      "name": "Mysore Masala Dosa",
      "restaurant": "Vaishali",
      "pricePaise": 14000
    }
  ]
}
```

### Case 3: `"masala dosa" -mysore`

**Why:** search-box syntax.

Request

``` code
POST /dishes/search HTTP/1.1

city=pune
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 129

{
  "q": "\"masala dosa\" -mysore",
  "city": "pune",
  "dishes": [
    {
      "id": 5,
      "name": "Masala Dosa",
      "restaurant": "Vaishali",
      "pricePaise": 12000
    }
  ]
}
```

### Case 4: panner

**Why:** empty: full-text matches words, not spellings.

Request

``` code
POST /dishes/search HTTP/1.1

city=pune
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 40

{
  "q": "panner",
  "city": "pune",
  "dishes": []
}
```

### Case 5: p

**Why:** `400`; one letter is not a search.

Request

``` code
POST /dishes/search HTTP/1.1

city=pune
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Validation failure",
  "instance": "/dishes/search",
  "status": 400,
  "title": "Bad Request"
}
```

## What PostgreSQL does to the words

Asked directly in `psql` (`docs/captures/words.txt`).

``` code
                      stored                      |      searched      |             syntax             
--------------------------------------------------+--------------------+--------------------------------
 'dosa':5 'masala':3 'paneer':1 'tikka':2 'two':4 | 'tikka' & 'paneer' | 'masala' <-> 'dosa' & !'mysor'
(1 row)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                | What happens                       | Proved by                                                |
|-----------------------------------------------------|------------------------------------|----------------------------------------------------------|
| Both words, in name or description                  | Name matches first                 | `paneerTikkaFindsEveryDishWithBothWordsNameMatchesFirst` |
| Capitals, other word order, plurals                 | Same results                       | `caseWordOrderAndPluralsDoNotMatter`                     |
| Phrases, exclusions, or                             | Understood                         | `searchSyntaxPeopleAlreadyKnow`                          |
| `& | ! ( :*`                                        | Ignored, not a 500                 | `oddCharactersAreSearchedNotParsed`                      |
| Stop words only; another city                       | Empty                              | `noMatchIsAnEmptyList`                                   |
| A typo                                              | Empty: the limit                   | `aTypoFindsNothingThatIsTheLimit`                        |
| Writing the search column directly; renaming a dish | Refused; the words follow the name | `theSearchColumnIsKeptByTheDatabaseNotByTheApp`          |
| Bad rows; a half-added menu                         | Refused; rolled back               | `DishDatabaseTest`                                       |

## The trap

Plausible but wrong

`LIKE '%term%'` that cannot use an index and misses word forms.

The old query is kept in the test: `name LIKE '%' || :q || '%'`.

- **Misses.** "paneer tikka" finds nothing (the menu says "Paneer"); "Paneer Tikka" misses Butter Chicken (descriptions were never searched); "Tikka Paneer" and "Masala Dosas" find nothing.
- **Reads.** A B-tree is sorted from the first character; `'%Paneer%'` has no first character to start from. PostgreSQL narrowed by city, then read every Pune dish's name: 4823 pages. The full-text search read 69.
- **The first fix that breaks.** `to_tsquery` expects its own syntax: `to_tsquery('english', 'paneer tikka')` is "syntax error in tsquery", a `500` for an ordinary search. `websearch_to_tsquery` never fails on what people type.

While building, each fix was undone once: `to_tsquery` turned 6 tests red; the name alone in the vector 4; the `simple` configuration (no stemming) 3; no ranking 2; no GIN index 1; `plainto_tsquery` 1 (no phrases or exclusions); no lower-casing of the city 1.

``` code
                                   QUERY PLAN                                   
--------------------------------------------------------------------------------
 Limit (actual rows=3 loops=1)
   Buffers: shared hit=4823
   ->  Sort (actual rows=3 loops=1)
         Sort Key: id
         Sort Method: quicksort  Memory: 25kB
         Buffers: shared hit=4823
         ->  Bitmap Heap Scan on dishes (actual rows=3 loops=1)
               Recheck Cond: ((city)::text = 'pune'::text)
               Filter: ((name)::text ~~ '%Paneer%'::text)
               Rows Removed by Filter: 66670
               Heap Blocks: exact=4762
               Buffers: shared hit=4820
               ->  Bitmap Index Scan on dishes_city (actual rows=66673 loops=1)
                     Index Cond: ((city)::text = 'pune'::text)
                     Buffers: shared hit=58
 Planning:
   Buffers: shared hit=118
(17 rows)
```

``` code
                                            QUERY PLAN                                             
---------------------------------------------------------------------------------------------------
 Limit (actual rows=4 loops=1)
   Buffers: shared hit=69
   ->  Sort (actual rows=4 loops=1)
         Sort Key: (ts_rank(dishes.search, '''paneer'''::tsquery)) DESC, dishes.id
         Sort Method: quicksort  Memory: 25kB
         Buffers: shared hit=69
         ->  Bitmap Heap Scan on dishes (actual rows=4 loops=1)
               Recheck Cond: ((search @@ '''paneer'''::tsquery) AND ((city)::text = 'pune'::text))
               Heap Blocks: exact=1
               Buffers: shared hit=63
               ->  BitmapAnd (actual rows=0 loops=1)
                     Buffers: shared hit=62
                     ->  Bitmap Index Scan on dishes_search (actual rows=5 loops=1)
                           Index Cond: (search @@ '''paneer'''::tsquery)
                           Buffers: shared hit=4
                     ->  Bitmap Index Scan on dishes_city (actual rows=66673 loops=1)
                           Index Cond: ((city)::text = 'pune'::text)
                           Buffers: shared hit=58
 Planning:
   Buffers: shared hit=161
(20 rows)
```

``` code
package com.tiffino.dishes;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Written first. The old LIKE search on the same 200,008 dishes: what it misses, and what it reads. */
class LikeSearchTrapTest extends ApiTest {

    static final String OLD = "SELECT name FROM dishes WHERE city = :city AND name LIKE '%' || :q || '%' ORDER BY id LIMIT 20";

    private List<String> old(String q) {
        return jdbc.sql(OLD).param("q", q).param("city", "pune").query(String.class).list();
    }

    @Test
    void likeMissesCaseWordOrderPluralsAndDescriptions() {
        assertThat(old("paneer tikka")).isEmpty();                                    // the menu says "Paneer"
        assertThat(old("Paneer Tikka")).containsExactly("Paneer Tikka Masala", "Paneer Tikka", "Tandoori Paneer Tikka Roll");   // not Butter Chicken
        assertThat(old("Tikka Paneer")).isEmpty();
        assertThat(old("Masala Dosas")).isEmpty();
        assertThat(new DishSearchProbe(jdbc).names("paneer tikka")).hasSize(4);
        assertThat(new DishSearchProbe(jdbc).names("Masala Dosas")).hasSize(2);
    }

    @Test
    void likeWithALeadingWildcardReadsEveryDishInTheCityTheGinIndexReadsAFew() {
        Plan like = explain(OLD, Map.of("q", "Paneer", "city", "pune"));   // the old query exactly, spelled as the menu does
        Plan fullText = explain(DishSearch.SQL, Map.of("q", "paneer", "city", "pune"));
        assertThat(like.indexes()).doesNotContain("dishes_search");   // at best it narrows by city, then reads the name of every Pune dish
        assertThat(fullText.indexes()).contains("dishes_search");
        assertThat(like.pages()).isGreaterThan(20 * fullText.pages());
    }

    @Test
    void toTsqueryOnWhatPeopleTypeIsASyntaxError() {
        assertThatThrownBy(() -> jdbc.sql("SELECT to_tsquery('english', :q)").param("q", "paneer tikka").query(String.class).single())
                .rootCause().hasMessageContaining("syntax error in tsquery");
        assertThat(jdbc.sql("SELECT websearch_to_tsquery('english', :q)::text").param("q", "paneer tikka").query(String.class).single())
                .isEqualTo("'paneer' & 'tikka'");
    }

    /** The new search's SQL, read back as names, so the old and new can sit side by side. */
    record DishSearchProbe(org.springframework.jdbc.core.simple.JdbcClient jdbc) {
        List<String> names(String q) {
            return jdbc.sql(DishSearch.SQL).param("q", q).param("city", "pune").query((rs, i) -> rs.getString("name")).list();
        }
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
./mvnw spring-boot:run      # the API on http://localhost:8080; the first start loads 200,008 dishes
./mvnw test                 # all 13 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

See how text becomes words, and how a search matches them:

``` code
docker compose exec postgres psql -U tiffino -d tiffino
SELECT to_tsvector('english', 'The spiciest dosas in Pune');
SELECT to_tsvector('english', 'Masala Dosa') @@ websearch_to_tsquery('english', 'dosas');
SELECT to_tsquery('english', 'paneer tikka');   -- the error people meet first
```

## Troubleshooting

| You see                                                                                     | Cause                                           | Fix                                                          |
|---------------------------------------------------------------------------------------------|-------------------------------------------------|--------------------------------------------------------------|
| `syntax error in tsquery`                                                                   | `to_tsquery` given text with spaces or symbols. | `websearch_to_tsquery` for anything a person typed.          |
| `cannot insert a non-DEFAULT value into column "search"`                                    | Code writing the generated column.              | Leave it out; PostgreSQL computes it.                        |
| `text-search query contains only stop words or doesn't contain lexemes, ignored` (a notice) | Only stop words were searched.                  | Expected; the result is empty.                               |
| The test's error message lacks the PostgreSQL text                                          | Spring's exception wraps it.                    | Assert on the root cause. Found while building this station. |

## Project layout

``` tree
stations/064-dish-search-with-postgresql-full-text/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/tiffino/dishes/
│   ├── DishController.java   ├── DishSearch.java   └── DishesApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__dishes.sql, V2__demo_dishes.sql, V3__search_index.sql
├── src/test/java/com/tiffino/dishes/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/tiffino/dishes/DishController.java`

Does  
Checks the length of q and the city, lower-cases the city.

Why  
One-letter searches and huge inputs never reach the database.

Without it  
"p" matching nothing useful after a full scan.

#### `src/main/java/com/tiffino/dishes/DishSearch.java`

Does  
One SQL query: parse, match through the index, rank, top 20.

Why  
`websearch_to_tsquery` once, reused for match and rank.

Without it  
`LIKE`, or a `to_tsquery` that fails on spaces.

#### `src/main/resources/db/migration/V1__dishes.sql`

Does  
The table, with `search` as a generated column.

Why  
PostgreSQL rebuilds the words whenever the name or description changes; no app code can forget.

Without it  
A search column that drifts from the menu.

#### `src/main/resources/db/migration/V3__search_index.sql`

Does  
The GIN index on `search`, and one on city.

Why  
The search reads only the rows containing the words.

Without it  
A full read of every dish in the city.

#### `src/main/resources/db/migration/V2__demo_dishes.sql`

8 dishes by hand, 200,000 generated.

#### `src/main/resources/application.yaml`

Problem details on.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/tiffino/dishes/DishesApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class               | Result |
|---------------|-------------------------------------------------------|--------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found (empty)      | `DishContractTest` (7)   | pass   |
| Every station | Reproduce the failure before the fix                  | `LikeSearchTrapTest` (3) | pass   |
| Database      | Rollback and constraint tests against a real database | `DishDatabaseTest` (3)   | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 7, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.dishes.DishContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.dishes.LikeSearchTrapTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.dishes.DishDatabaseTest
[INFO] Tests run: 13, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/tiffino/dishes/LikeSearchTrapTest.java`

Written first: what LIKE misses, what it reads, and the `to_tsquery` error.

#### `src/test/java/com/tiffino/dishes/DishDatabaseTest.java`

Named constraints, the generated column, and a rolled-back menu.

#### `src/test/java/com/tiffino/dishes/DishContractTest.java`

The endpoint through HTTP.

#### `src/test/java/com/tiffino/dishes/ApiTest.java`

Shared setup and the EXPLAIN reader.

#### `src/test/java/com/tiffino/dishes/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/tiffino/dishes/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=MaxPriceChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 13 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 16 tests pass (13 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## Within budget

Add `maxPrice` in whole rupees: only dishes at or under it, still ranked. Negative is `400`.

**Done when:** the test in `MaxPriceChallengeTest` passes.

Hints

- One more condition on `price_paise`, bound as a parameter.
- Keep `DishSearch.SQL` as it is: the trap test runs it.

#### `challenge/MaxPriceChallengeTest.java`

``` code
package com.tiffino.dishes;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.containsInAnyOrder;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: maxPrice (whole rupees) keeps only dishes at or under that price, still ranked. Negative is 400. */
class MaxPriceChallengeTest extends ApiTest {

    @Test
    void onlyDishesWithinBudget() throws Exception {
        mvc.perform(get("/dishes/search").param("q", "paneer tikka").param("city", "pune").param("maxPrice", "300")).andExpect(status().isOk())
                .andExpect(jsonPath("$.dishes[*].name", containsInAnyOrder("Paneer Tikka", "Tandoori Paneer Tikka Roll")));
        mvc.perform(get("/dishes/search").param("q", "paneer").param("city", "pune").param("maxPrice", "-1")).andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Did you mean…

When nothing matches, return `suggestions`: up to 5 dish names in the city that look like what was typed.

**Done when:** both tests in `DidYouMeanChallengeTest` pass.

Hints

- The `pg_trgm` extension compares three-letter pieces: `lower(name) % lower(:q)` and `similarity(…)`.
- Add `CREATE EXTENSION pg_trgm` and a GIN `gin_trgm_ops` index in a new migration.
- Found while building: that index on `lower(name)` also makes `lower(name) LIKE '%paneer%'` indexable.

#### `challenge/DidYouMeanChallengeTest.java`

``` code
package com.tiffino.dishes;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.empty;
import static org.hamcrest.Matchers.hasItem;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: when full-text finds nothing, "suggestions" lists up to 5 dish names in the city that look like what
 * was typed (pg_trgm similarity), so "panner" can offer "Paneer Tikka". When it finds something, no suggestions.
 */
class DidYouMeanChallengeTest extends ApiTest {

    @Test
    void aTypoGetsSuggestions() throws Exception {
        mvc.perform(get("/dishes/search").param("q", "panner tika").param("city", "pune")).andExpect(status().isOk())
                .andExpect(jsonPath("$.dishes", empty())).andExpect(jsonPath("$.suggestions", hasItem("Paneer Tikka")));
    }

    @Test
    void aHitNeedsNoSuggestions() throws Exception {
        mvc.perform(get("/dishes/search").param("q", "paneer").param("city", "pune")).andExpect(status().isOk())
                .andExpect(jsonPath("$.suggestions", empty()));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## When is a search engine worth it?

Product wants Hindi and Marathi names, "paneer" to find "cottage cheese", typo tolerance everywhere, results boosted by popularity and distance, and suggestions as you type, on 3 million dishes. Which can PostgreSQL do (configurations, synonym dictionaries, pg_trgm), and which point to OpenSearch or Elasticsearch? What does keeping a second copy in sync cost, and how stale can a search result be?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: what LIKE misses and what it reads.
2.  Add a weighted, generated `tsvector` column and a GIN index.
3.  Parse with `websearch_to_tsquery`, match with `@@`, rank with `ts_rank`.
4.  Prove the index is used with EXPLAIN, and test the limits (typos, stop words).

## Design alternatives and trade-offs

| Approach                                        | What it costs                                                  | Verdict                |
|-------------------------------------------------|----------------------------------------------------------------|------------------------|
| Generated tsvector + GIN + websearch_to_tsquery | One column and index; English only.                            | Chosen                 |
| `LIKE '%term%'`                                 | Misses forms and case; reads every row.                        | The trap               |
| `ILIKE` + pg_trgm index                         | Indexed and typo-friendly; no stemming or ranking by words.    | Good for names         |
| `to_tsvector(…)` in the query, expression index | No extra column; every query must repeat the exact expression. | Works                  |
| A tsvector kept by app code or a trigger        | Easy to forget a path that changes the name.                   | Generated is simpler   |
| OpenSearch / Elasticsearch                      | A second store kept in sync.                                   | For relevance at scale |

## Database design

| Object                                                             | What                                                                           | Why                                              |
|--------------------------------------------------------------------|--------------------------------------------------------------------------------|--------------------------------------------------|
| `search`                                                           | `tsvector GENERATED ALWAYS AS (…) STORED`: name weight A, description weight B | Always matches the current name and description. |
| `dishes_search`                                                    | GIN on `search`                                                                | Rows per word.                                   |
| `dishes_city`                                                      | B-tree on `city`                                                               | Every search is in one city.                     |
| `dishes_city_shape`, `dishes_name_not_blank`, `dishes_price_range` | CHECKs                                                                         | No impossible dishes from any writer.            |

``` code
CREATE TABLE dishes (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city        VARCHAR(30)  NOT NULL CONSTRAINT dishes_city_shape CHECK (city ~ '^[a-z-]{3,30}$'),
    restaurant  VARCHAR(100) NOT NULL,
    name        VARCHAR(100) NOT NULL CONSTRAINT dishes_name_not_blank CHECK (btrim(name) <> ''),
    description VARCHAR(500),
    price_paise INTEGER      NOT NULL CONSTRAINT dishes_price_range CHECK (price_paise BETWEEN 1000 AND 500000),
    -- Kept by PostgreSQL itself: the words of the name (weight A) and the description (weight B), stemmed in English.
    search      TSVECTOR GENERATED ALWAYS AS (
                    setweight(to_tsvector('english', name), 'A') || setweight(to_tsvector('english', coalesce(description, '')), 'B')) STORED
);
```

``` code
-- A GIN index holds, for every word, the list of dishes containing it: a search reads only those lists.
CREATE INDEX dishes_search ON dishes USING GIN (search);
CREATE INDEX dishes_city ON dishes (city);
ANALYZE dishes;
```

# 3 · Go deeper: Production

Adding the column to a big table  
A stored generated column rewrites the table when added. On 3 million rows, plan it: a new table and a backfill, or a maintenance window.

GIN and writes  
GIN indexes are slower to update than B-trees; PostgreSQL batches new entries in a pending list (`fastupdate`), cleaned by vacuum.

Language  
The `english` configuration stems English words. Indian dish names stem oddly or not at all; test with real menus.

Ranking cost  
`ts_rank` reads each match's vector. For a word in a million dishes, cap the work, for example rank only the first matches.

# 3 · Go deeper: Interview

## Interview takeaways

Why can't LIKE '%term%' use a B-tree index?

A B-tree is sorted from the first character; a leading wildcard gives no starting point, so every row must be checked. A trigram index can help; a B-tree cannot.

What are tsvector and tsquery?

A tsvector is a document as normalised words with positions; a tsquery is words joined with AND, OR, NOT; @@ tests whether one matches the other.

to_tsquery, plainto_tsquery or websearch_to_tsquery?

to_tsquery takes its own operator syntax and fails on plain text; plainto_tsquery ANDs all words; websearch_to_tsquery also understands quotes, -word and or, and never errors.

Why a GIN index?

It maps each word to the rows containing it, so a search reads only those rows.

When do you need a search engine instead?

Typo tolerance, synonyms, many languages, relevance tuning and facets at large scale: things PostgreSQL does only partly, at the cost of a second store kept in sync.

## Self-check rubric

| Area        | Meets the bar                                | Above the bar                              |
|-------------|----------------------------------------------|--------------------------------------------|
| Correctness | All 13 tests pass.                           | You read both saved plans.                 |
| Full-text   | Generated tsvector and websearch_to_tsquery. | Weights and ranking.                       |
| Indexes     | GIN used, proved by EXPLAIN.                 | Why the trigram index made LIKE indexable. |
| Limits      | Knows typos find nothing.                    | Can argue for or against a search engine.  |

# 3 · Go deeper: Review

## No reviewer view for this station

This station has no flawed version to review. Use this checklist on any text search:

- Is user text ever passed to `to_tsquery`?
- Can the search vector drift from the text it describes?
- Does an EXPLAIN show the index on realistic data?
- Are the limits (typos, languages) tested and stated?
