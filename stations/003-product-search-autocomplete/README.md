# Station 003 · Product search autocomplete

Foundations · 0–1 years · Core · E-commerce · Types: none

Spring Boot 4.1.1 · Java 25 · Spring MVC · TreeMap · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** 26 products are a fixed list inside the app; a test adds 2 lakh generated ones to measure the index. Nothing reads a real catalogue.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 19 tests.

# 1 · Understand

## The problem in real life

1.  **Ravi wants a new phone**

    He types *sam* into Kartwala's search box and waits for suggestions.

2.  **Nothing useful happens**

    Suggestions appear only after he types the whole word. When they do, "Balsamic Vinegar" sits next to Samsung phones, because the server looks for "sam" anywhere in each of 2 lakh names, on every keystroke.

3.  **The fix**

    The server keeps product names in sorted order and reads only the ones that start a word with "sam", most popular first.

Searching everything for every keystroke is slow and gives odd results. Sorting once, ahead of time, makes each keystroke cheap.

## What are we building?

`GET /suggestions?prefix=sam&limit=5`: up to 5 products with a word that starts with the typed text, most popular first. Letter case and extra spaces do not matter; a too-short or too-long prefix is refused.

## An everyday analogy

To find words starting with "sam" in a dictionary, you do not read every page. You open it near "sam", read down until the words stop starting with "sam", and close it. A sorted map lets the program do the same: jump to "sam", read the matching slice, stop.

## How it works in 4 steps

1.  **At start-up**, every product is stored in a sorted map under each word of its name: "Samsung Galaxy M35" under "samsung…", "galaxy…" and "m35…".
2.  **A keystroke arrives**. The prefix is normalised: lower case, trimmed, single spaces. Under 2 or over 40 characters: `400`.
3.  **Range lookup**: read only the keys from "sam" up to the last key that starts with "sam".
4.  **Rank** those products by popularity, remove duplicates, keep the top N.

Check yourself: why does "vinegar" find "Balsamic Vinegar 500ml", but "amic" finds nothing?

The product is stored under each word start: "balsamic…", "vinegar…" and "500ml". "vinegar" is the start of one of those keys. "amic" is in the middle of a word, and no key starts with it.

## What this station is not

- **Not a real catalogue.** 26 products are fixed in the code. A test builds an index of 2 lakh generated products to show the difference in work.
- **No spelling correction.** "samsng" finds nothing. Typo tolerance needs a search engine (a later station).
- **No live updates.** The index is built once at start-up; adding products while running is not covered.

## Key terms

| Term             | Simple meaning                                            | Everyday example                                                                 | In this project                            |
|------------------|-----------------------------------------------------------|----------------------------------------------------------------------------------|--------------------------------------------|
| **Autocomplete** | Suggestions shown while you are still typing.             | A friend finishing your sentence.                                                | Typing `sam` shows Samsung phones.         |
| **Prefix**       | The beginning of a word.                                  | "Sam" is the prefix of "Samsung".                                                | The `prefix` parameter.                    |
| **Normalise**    | Bring text to one standard form before comparing.         | Writing every name in capitals on a guest list.                                  | Lower case, trimmed, single spaces.        |
| **TreeMap**      | A Java map that keeps its keys sorted.                    | A dictionary: words in alphabetical order.                                       | `SuggestionIndex`.                         |
| **Range lookup** | Reading only the keys between two values in a sorted map. | Opening a dictionary at "sam" and reading until the words stop starting with it. | `subMap("sam", "sam\uffff")`.              |
| **Top-N**        | The N best items by some score.                           | The 5 best-selling books this week.                                              | The 5 most popular matches.                |
| **Index**        | A structure built ahead of time so lookups are fast.      | The index at the back of a book.                                                 | Built once at start-up from the catalogue. |

# 2 · Build: Spec

## Business problem

**Kartwala** (a fictional e-commerce marketplace) has about 2 lakh products. Its search box suggests nothing useful until a whole word is typed. The suggestion API loops over every product name and calls `contains()` on each keystroke, so it is slow, and it returns odd matches such as "Balsamic Vinegar" for "sam", in catalogue order rather than by popularity.

Customers who cannot find a product quickly leave. The search team wants suggestions from the second character, in under a few milliseconds, ranked by what people actually buy.

## Acceptance criteria

1.  **Given** `prefix=sam`, **then** the 5 most popular products with a word starting with "sam" are returned, each with its id and name.
2.  **Given** `prefix=galaxy`, **then** products whose second word starts with "galaxy" are found too.
3.  **Given** `prefix=msung` (inside "Samsung"), **then** no suggestions.
4.  **Given** ` SAMSUNG galaxy s`, **then** the same results as `samsung galaxy s`.
5.  **Given** a prefix under 2 or over 40 characters after trimming, a missing prefix, or a limit outside 1–10, **then** `400`.
6.  **Given** 2 lakh products, **when** searching "sam", **then** only the matching entries are read, not every name.

## Requirements

- Matching is by word start, case-insensitive, with `Locale.ROOT`.
- Results are ordered by popularity (highest first), then by name; each product appears once.
- Names are returned in their original spelling (`boAt`, not `boat`).
- `prefix` is required: 2 to 40 characters after normalising. Raw input over 200 characters is rejected before any work.
- `limit`: 1 to 10, default 5. No match is `200` with an empty list.

## Learning objectives

- Use a `TreeMap` and `subMap` for a prefix range lookup.
- Normalise text the same way when storing and when searching.
- Rank with a `Comparator` and take the top N.
- Explain why input length limits protect the server.
- Count the work an algorithm does, instead of guessing.

# 2 · Build: API contract

## Endpoint

| Method | Path                        | Purpose                                                                      |
|--------|-----------------------------|------------------------------------------------------------------------------|
| `GET`  | `/suggestions?prefix&limit` | Products whose name has a word starting with the prefix, most popular first. |

## Parameters

| Parameter | Type    | Default  | Rule                                                                                     |
|-----------|---------|----------|------------------------------------------------------------------------------------------|
| `prefix`  | string  | required | 2 to 40 characters after trimming and collapsing spaces; at most 200 characters as sent. |
| `limit`   | integer | 5        | 1 to 10.                                                                                 |

## Status codes

| Status | When                                                       | Body                                                         |
|--------|------------------------------------------------------------|--------------------------------------------------------------|
| 200    | Any valid prefix, even with no match                       | `prefix` (normalised) and `suggestions`: `productId`, `name` |
| 400    | Missing prefix, too short, too long, or limit out of range | Problem: *Invalid prefix*, or `errors` per parameter         |

## Captured examples

Captured with curl from the running app on 13 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: the customer types "sam"

**Why:** five products have a word starting with "sam"; they come back most popular first. Balsamic Vinegar is not among them: "sam" is in the middle of its word.

Request

``` code
GET /suggestions?prefix=sam HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 262

{
  "prefix": "sam",
  "suggestions": [
    {
      "productId": 1,
      "name": "Samsung Galaxy M35 5G"
    },
    {
      "productId": 2,
      "name": "Samsung Galaxy S24"
    },
    {
      "productId": 4,
      "name": "Sambar Masala 100g"
    },
    {
      "productId": 3,
      "name": "Samsung 55-inch Crystal TV"
    },
    {
      "productId": 5,
      "name": "Samosa Party Pack"
    }
  ]
}
```

### Case 2: a later word, in capitals

**Why:** the prefix is normalised to "galaxy", and products are stored under every word start, so a second word matches too.

Request

``` code
GET /suggestions?prefix=GALAXY&limit=3 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 173

{
  "prefix": "galaxy",
  "suggestions": [
    {
      "productId": 1,
      "name": "Samsung Galaxy M35 5G"
    },
    {
      "productId": 2,
      "name": "Samsung Galaxy S24"
    },
    {
      "productId": 10,
      "name": "Galaxy Chocolate Bar"
    }
  ]
}
```

### Case 3: text inside a word

**Why:** "msung" starts no word of any product, so the list is empty. `200`: an empty result is a valid answer.

Request

``` code
GET /suggestions?prefix=msung HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 35

{
  "prefix": "msung",
  "suggestions": []
}
```

### Case 4: one letter

**Why:** one letter would match a large share of the catalogue and help nobody, so the server refuses it with `400`.

Request

``` code
GET /suggestions?prefix=s HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "The prefix must be 2 to 40 characters after trimming spaces.",
  "instance": "/suggestions",
  "status": 400,
  "title": "Invalid prefix"
}
```

### Case 5: limit too high

**Why:** a search box shows at most 10; the cap is checked before any work.

Request

``` code
GET /suggestions?prefix=sam&limit=50 HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "The search parameters are invalid.",
  "instance": "/suggestions",
  "status": 400,
  "title": "Bad Request",
  "errors": {
    "limit": "must be less than or equal to 10"
  }
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                               | What the API does                                       | Proved by                                                                                                                       |
|----------------------------------------------------|---------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| "sam"                                              | Top 5 word-start matches, by popularity                 | `theIndexSuggestsOnlyWordStartsMostPopularFirst`, `prefixReturnsTheMostPopularMatchesWithIds`                                   |
| A later word ("galaxy")                            | Matches                                                 | `anyWordOfTheNameCanStartTheMatch`                                                                                              |
| Text inside a word ("msung")                       | No match                                                | `textInTheMiddleOfAWordIsNotAMatch`                                                                                             |
| Capitals and extra spaces                          | Normalised before matching                              | `letterCaseAndExtraSpacesDoNotMatter`                                                                                           |
| Mixed-case brand names                             | Returned as spelled                                     | `theNameKeepsItsOriginalSpelling`                                                                                               |
| Two words of one product match                     | Suggested once                                          | `aProductMatchingTwoWordsIsSuggestedOnce`                                                                                       |
| Equal popularity                                   | Ordered by name                                         | `equalPopularityIsOrderedByName`                                                                                                |
| "Samz" against "San"                               | The range stops exactly where the prefix stops matching | `theRangeEndsWhereThePrefixStopsMatching`                                                                                       |
| Turkish server locale                              | "IPHONE" still finds iPhone                             | `aTurkishServerLocaleDoesNotChangeMatching`                                                                                     |
| No match                                           | `200`, empty list                                       | `noMatchIsAnEmptyListNotAnError`                                                                                                |
| Missing, 1-letter, 41-letter or 5000-letter prefix | `400`                                                   | `missingPrefixIs400`, `oneLetterAfterTrimmingIs400`, `aPrefixLongerThan40CharactersIs400`, `aHugePrefixIsRejectedBeforeAnyWork` |
| Limit 0 or 11                                      | `400`                                                   | `limitOutsideOneToTenIs400`                                                                                                     |

## The trap

Plausible but wrong

Scanning every product name with `contains()` on each keystroke.

It is the first idea most people have, and it works on a list of 20. It has two problems. It matches text anywhere, so "sam" suggests Balsamic Vinegar. And it reads every name on every keystroke: with 2 lakh products, typing "samsung" means 7 full scans. The first test shows the odd match through a "before" controller. The last one counts the work on 2 lakh generated products: the scan reads every name, the index reads 5 entries. Indexing every character position instead of word starts was tried while building: 2 tests went red.

``` code
package com.kartwala.search;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.IntStream;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.hasItem;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.not;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * The first test written for this station: it reproduces the bug before the fix.
 * The customer types "sam" into the search box.
 */
@Import(ContainsScanTrapTest.NaiveSuggestionController.class)
class ContainsScanTrapTest extends ApiTest {

    /** The "before" code: on every keystroke, look at every product name and keep those containing the text. */
    @RestController
    static class NaiveSuggestionController {
        @GetMapping("/naive/suggestions")
        List<String> suggestions(@RequestParam String prefix) {
            return ProductCatalog.PRODUCTS.stream()
                    .map(Product::name)
                    .filter(name -> name.toLowerCase().contains(prefix.toLowerCase()))
                    .toList();
        }
    }

    @Test
    void containsSuggestsBalsamicVinegarForSam() throws Exception {
        mvc.perform(get("/naive/suggestions").param("prefix", "sam"))
                .andExpect(jsonPath("$", hasSize(6)))
                .andExpect(jsonPath("$", hasItem("Balsamic Vinegar 500ml")));  // "sam" in the middle of a word
    }

    @Test
    void theIndexSuggestsOnlyWordStartsMostPopularFirst() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "sam"))
                .andExpect(jsonPath("$.suggestions[*].name", not(hasItem("Balsamic Vinegar 500ml"))))
                .andExpect(jsonPath("$.suggestions[*].name", contains(
                        "Samsung Galaxy M35 5G", "Samsung Galaxy S24", "Sambar Masala 100g", "Samsung 55-inch Crystal TV", "Samosa Party Pack")));
    }

    @Test
    void withTwoLakhProductsTheScanReadsEveryNameButTheIndexReadsOnlyTheMatches() {
        List<Product> products = new ArrayList<>(ProductCatalog.PRODUCTS);
        IntStream.rangeClosed(1, 200_000).forEach(i -> products.add(new Product(1000 + i, "Item %06d".formatted(i), 1)));

        long namesReadByScan = products.size();                        // contains() has to look at every name
        int entriesReadByIndex = new SuggestionIndex(products).candidates("sam").size();

        assertThat(namesReadByScan).isEqualTo(200_026);
        assertThat(entriesReadByIndex).isEqualTo(5);                   // the five products with a word starting "sam"
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
./mvnw test                 # all 19 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Type a product the way a customer would, one letter more each time:

``` code
curl "http://localhost:8080/suggestions?prefix=sa"
curl "http://localhost:8080/suggestions?prefix=sam"
curl "http://localhost:8080/suggestions?prefix=sams"

# A second word works too
curl "http://localhost:8080/suggestions?prefix=gold"

# One letter: expect 400
curl -i "http://localhost:8080/suggestions?prefix=s"
```

## Troubleshooting

| You see                                           | Cause                        | Fix                                                      |
|---------------------------------------------------|------------------------------|----------------------------------------------------------|
| A space in the prefix gives an error in the shell | The shell splits the URL.    | Quote the URL, and write a space as `%20` or `+`.        |
| `release version 25 not supported`                | Maven is using an older JDK. | Point `JAVA_HOME` at JDK 25, or add `-Djava.version=21`. |
| `Port 8080 was already in use`                    | Another app uses the port.   | Stop it, or add `--server.port=8081` as an app argument. |

## Project layout

``` tree
stations/003-product-search-autocomplete/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/kartwala/search/
│   ├── SuggestionController.java   ├── SuggestionIndex.java
│   ├── ProductCatalog.java         ├── Product.java
│   ├── Suggestion.java             ├── ApiErrors.java
│   └── SearchApplication.java
├── src/test/java/com/kartwala/search/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/kartwala/search/SuggestionController.java`

Does  
Reads `prefix` and `limit`, normalises the prefix, checks its length, and returns the suggestions.

Why  
Length limits sit at the door, so a 5000-character prefix never reaches the index.

Without it  
No endpoint; and without the limits, one bad request could make the server do far too much work.

- Two checks on the prefix: `@Size(max = 200)` on the raw text, then 2–40 after normalising, because `" s "` is one letter.

#### `src/main/java/com/kartwala/search/SuggestionIndex.java`

Does  
Builds a sorted map from each word start to its product, and answers a prefix with a range lookup and a top-N.

Why  
Sorted keys put every match for a prefix side by side, so a lookup reads only that slice.

Without it  
Back to scanning every name on every keystroke.

- `normalise` is used for names and prefixes alike: if they were normalised differently, nothing would match.
- The `\u0000` and id at the end of each key keep keys unique when products share a word.
- `prefix + Character.MAX_VALUE` is the end of the range: just past every key that starts with the prefix.

#### `src/main/java/com/kartwala/search/ProductCatalog.java`

The 26 products, with popularity (orders in the last 30 days).

#### `src/main/java/com/kartwala/search/Product.java`

A product: id, name, popularity.

#### `src/main/java/com/kartwala/search/Suggestion.java`

The response: the normalised prefix and the suggested items.

#### `src/main/java/com/kartwala/search/ApiErrors.java`

Does  
Adds an `errors` map (parameter → message) to validation failures.

Why  
The app learns which parameter was wrong.

Without it  
A bare "Bad Request".

#### `src/main/java/com/kartwala/search/SearchApplication.java`

Standard Spring Boot entry point.

#### `pom.xml`

Web MVC and validation; test starters for JUnit and MockMvc.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                              | Test class                    | Result |
|---------------|------------------------------------------|-------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found | `SuggestionContractTest` (12) | pass   |
| Every station | Reproduce the failure before the fix     | `ContainsScanTrapTest` (3)    | pass   |
| This station  | The index on its own                     | `SuggestionIndexTest` (4)     | pass   |

"Not found" for a search is an empty list, not a `404`: the contract tests check `200` with no suggestions.

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.search.ContainsScanTrapTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.search.SuggestionIndexTest
[INFO] Tests run: 12, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.search.SuggestionContractTest
[INFO] Tests run: 19, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/kartwala/search/ContainsScanTrapTest.java`

Written first: the odd match from `contains()`, the fixed ranking, and the work counted on 2 lakh products.

#### `src/test/java/com/kartwala/search/SuggestionContractTest.java`

Matches, ranking, normalising, empty results and every rejected input.

#### `src/test/java/com/kartwala/search/SuggestionIndexTest.java`

The index as plain Java: duplicates, ties, range edges and a Turkish locale.

#### `src/test/java/com/kartwala/search/ApiTest.java`

Shared setup: the whole app, called through MockMvc.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/kartwala/search/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=PunctuationChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 19 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 26 tests pass (19 station tests and 7 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Ignore punctuation

"parle g" should find Parle-G Biscuits, "55 inch" the 55-inch TV, and "head shoulders" the shampoo. Treat anything that is not a letter or a digit as a space, for names and prefixes alike.

**Done when:** all four tests in `PunctuationChallengeTest` pass, and the station's tests still pass.

Hints

- Change `normalise` only. Names and prefixes both go through it, so they stay in step.
- `\p{L}` is any letter and `\p{N}` any digit, in any language. `[^\p{L}\p{N}]+` is a run of anything else.
- Replace runs with one space, then `strip()`: "--&&--" becomes empty, which is too short.

#### `challenge/PunctuationChallengeTest.java`

``` code
package com.kartwala.search;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: punctuation in names or prefixes must not stop a match. */
class PunctuationChallengeTest extends ApiTest {

    @Test
    void aSpaceMatchesAHyphen() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "parle g"))
                .andExpect(jsonPath("$.suggestions[*].name", contains("Parle-G Biscuits")));
        mvc.perform(get("/suggestions").param("prefix", "55 inch"))
                .andExpect(jsonPath("$.suggestions[*].name", contains("Samsung 55-inch Crystal TV")));
    }

    @Test
    void aHyphenInThePrefixStillMatches() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "Parle-G"))
                .andExpect(jsonPath("$.prefix").value("parle g"))
                .andExpect(jsonPath("$.suggestions[*].name", contains("Parle-G Biscuits")));
    }

    @Test
    void anAmpersandIsIgnored() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "head shoulders"))
                .andExpect(jsonPath("$.suggestions[*].name", contains("Head & Shoulders Shampoo")));
    }

    @Test
    void onlyPunctuationIsTooShort() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "--&&--")).andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Hide out-of-stock products

Saffola Gold Oil 1L (id 8) is out of stock. Hide out-of-stock products unless the app sends `includeOutOfStock=true`, and add `inStock` to each suggestion.

**Done when:** all three tests in `OutOfStockChallengeTest` pass. The third proves the stock filter runs before the limit.

Hints

- Add `inStock` to `Product`, and keep a three-argument constructor so the station's tests still compile.
- Filter before `limit`. Station 002's trap, in a new place.
- A `boolean` parameter with `defaultValue = "false"` is all the controller needs.

#### `challenge/OutOfStockChallengeTest.java`

``` code
package com.kartwala.search;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/** Challenge 2: Saffola Gold Oil 1L (id 8) is out of stock. Hide it unless the app asks for out-of-stock items. */
class OutOfStockChallengeTest extends ApiTest {

    @Test
    void outOfStockProductsAreHiddenByDefault() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "saf"))
                .andExpect(jsonPath("$.suggestions[*].name", contains("Safari Suitcase Medium")));
    }

    @Test
    void theAppCanAskForThemAndSeesWhichAreOutOfStock() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "saf").param("includeOutOfStock", "true"))
                .andExpect(jsonPath("$.suggestions[*].name", contains("Saffola Gold Oil 1L", "Safari Suitcase Medium")))
                .andExpect(jsonPath("$.suggestions[0].inStock").value(false))
                .andExpect(jsonPath("$.suggestions[1].inStock").value(true));
    }

    @Test
    void hidingHappensBeforeTheLimitSoTheListStaysFull() throws Exception {
        // Saffola (8800) would be third. Filtered after the limit, the app would get only two suggestions.
        mvc.perform(get("/suggestions").param("prefix", "sa").param("limit", "3"))
                .andExpect(jsonPath("$.suggestions[*].name", contains("Samsung Galaxy M35 5G", "Tata Salt 1kg", "Samsung Galaxy S24")));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## "s" at peak traffic

Product wants suggestions from the first letter. Suppose "s" matches 30,000 of the 2 lakh products: each request would then sort 30,000 to show 5. How could you prepare the top 10 for every short prefix ahead of time? How much memory would that take for all 1- and 2-letter prefixes, and when would you rebuild it as popularity changes?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: `contains()` suggests Balsamic Vinegar and reads every name.
2.  Write `normalise`, used for names and prefixes alike.
3.  Build the `TreeMap` once: one key per word start, made unique with the product id.
4.  Answer with `subMap`, then rank by popularity, remove duplicates, take the top N.
5.  Guard the input: raw length, normalised length, limit range.

## Design alternatives and trade-offs

| Approach                                  | What it costs                                                                                       | Verdict         |
|-------------------------------------------|-----------------------------------------------------------------------------------------------------|-----------------|
| `TreeMap` of word starts, range lookup    | Memory for one key per word (about 4 per product). Lookup reads only matches.                       | Chosen          |
| Loop with `contains()`                    | Reads every name per keystroke; mid-word matches; no ranking.                                       | Wrong           |
| Loop with `startsWith()` on the full name | No odd matches, but still reads every name, and misses second words.                                | Wrong           |
| A trie (prefix tree)                      | The classic structure for prefixes; can store a top-10 at each node. More code than a TreeMap.      | At larger scale |
| SQL `LIKE 'sam%'` with an index           | Works for the start of a column, not for later words, and adds a database round trip per keystroke. | Possible        |
| A search engine (OpenSearch)              | Typos, synonyms, scoring and scale, with another system to run.                                     | Later stations  |

## Database design

None: the catalogue is fixed in code and the index lives in memory. Challenge 3 asks how you would keep a precomputed top-N up to date.

# 3 · Go deeper: Production

Security  
Two length checks stop expensive input. The prefix is echoed back only after normalising, as JSON data, never as HTML.

Performance  
The work is proportional to the matches, not to the catalogue. Short prefixes still match many products; Challenge 3 is the fix. Apps also usually wait a short moment after the last keystroke (debounce) before calling, so fast typists do not send every letter.

Reliability  
The index is rebuilt only at start-up, so new products appear after a restart. Good enough for this station, not for a live shop.

Cost  
About 4 keys per product: for 2 lakh products, around 8 lakh short strings in memory. Measure before you assume it fits.

# 3 · Go deeper: Interview

## Interview takeaways

How do you find every key with a given prefix in a TreeMap?

subMap(prefix, true, prefix + Character.MAX_VALUE, false). Keys are sorted, so all keys starting with the prefix sit between the prefix itself and the prefix followed by the highest character.

Why normalise both the stored names and the search text?

Matching compares strings exactly. If names are lower-cased but the prefix is not (or the other way round), nothing matches. One normalise method used for both keeps them in step.

Why toLowerCase(Locale.ROOT)?

Without a locale, Java uses the server's. On a Turkish server, 'I' lower-cases to a dotless 'ı', so 'IPHONE' would never match 'iphone'. Locale.ROOT gives the same result on every server.

Why limit the prefix length?

A minimum avoids returning a large share of the catalogue for one letter. A maximum, checked before any work, stops someone sending 5000 characters to every instance.

How do you prove an index is better than a scan?

Count the work, not just the time: the scan reads every name; the range lookup reads only matching entries. The trap test asserts 200,026 against 5.

## Self-check rubric

| Area        | Meets the bar                         | Above the bar                                              |
|-------------|---------------------------------------|------------------------------------------------------------|
| Correctness | All 19 tests pass.                    | You can say which test fails if mid-word keys are indexed. |
| Design      | One normalise method; a range lookup. | You can sketch a trie with a top-10 per node.              |
| Tests       | Contract, index and trap tests pass.  | You counted the work instead of timing it, and know why.   |
| Explanation | You can explain `subMap`'s two ends.  | You can explain the Turkish locale bug.                    |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on your own code instead:

- Are names and prefixes normalised by the same method?
- Does any code path read every product per request?
- Is every `toLowerCase` given `Locale.ROOT`?
- Is input length checked before the expensive part?
