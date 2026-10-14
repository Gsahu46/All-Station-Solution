# Station 020 · Bank statement pages

Foundations · 0–1 years · Core · Fintech · Types: none

Spring Boot 4.1.1 · Java 25 · Spring MVC · generics · Comparator chains · method validation · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The transactions are generated in memory from a fixed seed: no bank, no real account. The same 4,000 rows appear on every run.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 12 tests.

# 1 · Understand

## The problem in real life

1.  **Asha opens a year of statements on her phone**

    The app asks for all 4,000 transactions at once. The response takes so long on mobile data that the request times out.

2.  **A script asks for size=1000000**

    The server tries to load and serialise everything it has. On a real table, that is millions of rows, and the server runs out of memory.

3.  **The fix**

    Pages of at most 100, newest first in a fixed order, with a limit on how deep offset paging may go.

Every list endpoint needs a maximum page size. The client may ask; the server decides.

## What are we building?

`GET /accounts/{id}/transactions?page=0&size=20` returns one page of a statement, newest first, with the total count and whether there is a next page.

## An everyday analogy

A bank passbook printer prints a few pages at a time, not the whole year in one go. It always prints in the same order, so page 2 continues exactly where page 1 stopped.

## How it works in 4 steps

1.  **Check the request**: page from 0, size from 1 to 100, and not too deep.
2.  **Order the statement**: newest first; for the same minute, the higher id first.
3.  **Slice** page × size to page × size + size, computed as a `long`.
4.  **Answer** with the items, the totals and whether there is more.

Check yourself: 19 transactions were posted at 13:15 on one day. Sorting by time alone, which comes first?

Nothing in the time decides. In memory, Java's sort keeps them in whatever order they arrived; in a database, the order can change between two queries, so a row can appear on two pages or none. A tie-breaker (the id) makes the order total.

## What this station is not

- **Not cursor paging.** Offsets drift when new transactions arrive; station 66 (keyset pagination) fixes that.
- **No database.** The rows are generated in memory.
- **No filters or other sorts.** The challenges add them.

## Key terms

| Term                       | Simple meaning                                                             | Everyday example                                     | In this project        |
|----------------------------|----------------------------------------------------------------------------|------------------------------------------------------|------------------------|
| **Page**                   | One slice of a long list, with enough information to ask for the next one. | Page 3 of a printed passbook.                        | `Page<T>`              |
| **Offset paging**          | "Skip page × size rows, return size rows."                                 | Turning to page 40 by counting 39 pages first.       | `?page=1&size=20`      |
| **Generic class**          | A class written once for any element type.                                 | One envelope design for letters, bills or photos.    | `Page<Transaction>`    |
| **Bounded type parameter** | A generic type that must have some ability.                                | "Any envelope, as long as it has a tracking number." | `T extends Identified` |
| **Comparator chain**       | Sort by one thing, then by another to break ties.                          | Sort a class by marks, then by roll number.          | `STATEMENT_ORDER`      |
| **Integer overflow**       | A number too big for its type wraps around to a negative one.              | An odometer rolling past 99999 back to 00000.        | `(long) page * size`   |

# 2 · Build: Spec

## Business problem

**Tijori** (a fictional fintech app) serves statements with whatever page size the client sends. Phones asking for a year of transactions time out; one request for a million rows took the server down. A very large page number made the offset overflow and return a 500.

## Acceptance criteria

1.  **Given** no parameters, **then** the newest 20 transactions, 4,000 in total over 200 pages, with `hasNext` true.
2.  **Given** page 39 of size 100, **then** the last 100 and `hasNext` false; page 40 is empty, not an error.
3.  **Given** size 101, size 0, page −1 or page "abc", **then** `400`.
4.  **Given** page × size of 10,000 or more, **then** `400` "Page too deep".
5.  **Given** an unknown account, **then** `404`; an account with no transactions has 0 pages.
6.  **Given** any page size, **then** walking every page sees each transaction exactly once, in statement order.

## Requirements

- Pages start at 0; size defaults to 20, at most 100.
- Statement order: newest `postedAt` first, then the higher id first.
- Offsets are computed in `long`; page × size must be under 10,000 (a demo rule).
- Account ids are normalised with `Locale.ROOT`.

## Learning objectives

- Write a generic class, and use a bounded type parameter when the class needs something from its elements.
- Build a total order with a `Comparator` chain.
- Bound every list endpoint, and say why deep offsets are expensive.
- Spot an integer overflow before it becomes a 500.

# 2 · Build: API contract

## Endpoint

| Method | Path                                    | Purpose                                  |
|--------|-----------------------------------------|------------------------------------------|
| `GET`  | `/accounts/{id}/transactions?page&size` | One page of the statement, newest first. |

## Parameters

| Parameter     | Rule                        |
|---------------|-----------------------------|
| `page`        | 0 or more; default 0.       |
| `size`        | 1 to 100; default 20.       |
| `page × size` | Under 10,000 (a demo rule). |

## Response

| Field                      | Meaning                                                                                       |
|----------------------------|-----------------------------------------------------------------------------------------------|
| `items`                    | The transactions on this page. Negative amounts are debits.                                   |
| `page`, `size`             | What was asked for.                                                                           |
| `totalItems`, `totalPages` | For the whole statement.                                                                      |
| `hasNext`                  | Whether another page has items.                                                               |
| `lastId`                   | The id of the last item: where a cursor would continue (station 66). `null` on an empty page. |

## Status codes

| Status | When                                                         |
|--------|--------------------------------------------------------------|
| 200    | A page, possibly empty                                       |
| 400    | A parameter out of range or not a number, or a page too deep |
| 404    | No such account                                              |

## Captured examples

Captured with curl from the running app on 14 Oct 2026, in this order. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: the first page, size 3

**Why:** the newest three. `lastId` is the third item's id.

Request

``` code
GET /accounts/acc-1001/transactions?size=3 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 387

{
  "items": [
    {
      "id": 3998,
      "postedAt": "2026-10-02T18:45:00",
      "description": "Card at fuel station",
      "amountPaise": -62406
    },
    {
      "id": 4000,
      "postedAt": "2026-10-02T09:30:00",
      "description": "NEFT rent",
      "amountPaise": -138829
    },
    {
      "id": 3999,
      "postedAt": "2026-10-02T09:30:00",
      "description": "ATM withdrawal",
      "amountPaise": -22356
    }
  ],
  "page": 0,
  "size": 3,
  "totalItems": 4000,
  "totalPages": 1334,
  "hasNext": true,
  "lastId": 3999
}
```

### Case 2: the next page

**Why:** continues exactly after case 1's last item, because the order has a tie-breaker.

Request

``` code
GET /accounts/acc-1001/transactions?page=1&size=3 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 398

{
  "items": [
    {
      "id": 3997,
      "postedAt": "2026-10-02T09:30:00",
      "description": "UPI to grocer",
      "amountPaise": -18994
    },
    {
      "id": 3996,
      "postedAt": "2026-10-02T00:00:00",
      "description": "Card at fuel station",
      "amountPaise": -125543
    },
    {
      "id": 3988,
      "postedAt": "2026-10-01T18:45:00",
      "description": "Card at fuel station",
      "amountPaise": -121666
    }
  ],
  "page": 1,
  "size": 3,
  "totalItems": 4000,
  "totalPages": 1334,
  "hasNext": true,
  "lastId": 3988
}
```

### Case 3: page 40 of size 100

**Why:** 4,000 rows end at page 39. Past the end is an empty page, not an error.

Request

``` code
GET /accounts/acc-1001/transactions?page=40&size=100 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 97

{
  "items": [],
  "page": 40,
  "size": 100,
  "totalItems": 4000,
  "totalPages": 40,
  "hasNext": false,
  "lastId": null
}
```

### Case 4: size 1,000,000

**Why:** the request that took the old server down: `400`. Spring's default detail says only “Validation failure”; the limit of 100 is in the API contract above.

Request

``` code
GET /accounts/acc-1001/transactions?size=1000000 HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Validation failure",
  "instance": "/accounts/acc-1001/transactions",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 5: page 200,000,000

**Why:** page × size is 4,000,000,000: too deep, and too big for an `int`. `400`, not a 500.

Request

``` code
GET /accounts/acc-1001/transactions?page=200000000&size=20 HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "page x size must be under 10000. Narrow the request by date instead.",
  "instance": "/accounts/acc-1001/transactions",
  "status": 400,
  "title": "Page too deep"
}
```

### Case 6: an account with no transactions

**Why:** zero items and zero pages.

Request

``` code
GET /accounts/acc-1002/transactions HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 91

{
  "items": [],
  "page": 0,
  "size": 20,
  "totalItems": 0,
  "totalPages": 0,
  "hasNext": false,
  "lastId": null
}
```

### Case 7: an unknown account

**Why:** `404`.

Request

``` code
GET /accounts/acc-9999/transactions HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No account has the id acc-9999.",
  "instance": "/accounts/acc-9999/transactions",
  "status": 404,
  "title": "Account not found"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                    | What happens                         | Proved by                                              |
|---------------------------------------------------------|--------------------------------------|--------------------------------------------------------|
| No parameters, account id in capitals                   | Newest 20 of 4,000; 200 pages        | `theFirstPageIsTheNewestTwenty`                        |
| Page 39 and 40 of size 100                              | Last 100 then empty; `hasNext` false | `theLastPageHasNoNextAndPastTheEndIsEmpty`             |
| No transactions                                         | 0 items, 0 pages                     | `anAccountWithNoTransactionsHasNoPages`                |
| size 100 / 101 / 0; page −1, abc; offset 9,900 / 10,000 | OK / `400`                           | `outOfRangeParametersAre400`                           |
| Unknown account                                         | `404`                                | `anUnknownAccountIs404`                                |
| Every page at sizes 1, 7, 37, 100                       | Each transaction once, in order      | `walkingEveryPageSeesEachTransactionOnceInOrder`       |
| Up to 19 rows in one minute                             | Ordered by id, newest first          | `transactionsInTheSameMinuteAreOrderedByIdNewestFirst` |
| Empty list; a different element type                    | One empty page; `Page<Note>` works   | `PageTest`                                             |

## The trap

Plausible but wrong

Unbounded page size, so one request loads millions of rows.

"Let the client choose the page size" sounds friendly. The first test shows the old paging handing over all 4,000 rows for `size=1000000`. The second shows `page × size` overflowing an `int` into a negative offset. The third shows the fixed endpoint answering both with a `400`. Removing the size limit turned 2 tests red; dropping the tie-breaker turned 2 red. Computing the offset as an `int` again gave this, from a real run:

``` console
# ./mvnw test -Dtest=BottomlessPageTrapTest, with the offset computed as an int (page * size) instead of a long
GET /accounts/acc-1001/transactions?page=200000000&size=20
Request processing failed: java.lang.IndexOutOfBoundsException: fromIndex = -294967296
```

``` code
package com.tijori.statements;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The first test written for this station: it reproduces the bugs before the fix. */
class BottomlessPageTrapTest extends ApiTest {

    static final List<Transaction> STATEMENT = Accounts.generate(4_000);

    /** The "before" paging: any size, offset in int. Kept only in tests. */
    static List<Transaction> oldPage(int page, int size) {
        int from = Math.min(page * size, STATEMENT.size());
        return STATEMENT.subList(from, Math.min(from + size, STATEMENT.size()));
    }

    @Test
    void theOldCodeHandsOverTheWholeHistoryForOneLargeSize() {
        assertThat(oldPage(0, 1_000_000)).hasSize(4_000);   // here 4,000; on a real table, millions of rows in one response
    }

    @Test
    void theOldOffsetOverflowsIntoANegativeNumber() {
        assertThat(200_000_000 * 20).isNegative();          // 4,000,000,000 does not fit in an int
        assertThatThrownBy(() -> oldPage(200_000_000, 20)).isInstanceOf(IndexOutOfBoundsException.class);   // a 500
    }

    @Test
    void theFixedEndpointRefusesBothWithA400() throws Exception {
        transactions("acc-1001", "size", "1000000").andExpect(status().isBadRequest());
        transactions("acc-1001", "page", "200000000", "size", "20").andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.title").value("Page too deep"));
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
./mvnw test                 # all 12 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

``` code
# The newest 5, then the next 5
curl "http://localhost:8080/accounts/acc-1001/transactions?size=5"
curl "http://localhost:8080/accounts/acc-1001/transactions?page=1&size=5"

# The request that used to load everything: now a 400
curl -i "http://localhost:8080/accounts/acc-1001/transactions?size=1000000"
```

## Troubleshooting

| You see                            | Cause                          | Fix                                                                                     |
|------------------------------------|--------------------------------|-----------------------------------------------------------------------------------------|
| `400` Page too deep                | page × size is 10,000 or more. | Use a smaller page number; in a real app, filter by date (challenge 1) or use a cursor. |
| `400` for `page=1` on PowerShell   | `&` splits the command.        | Put the URL in double quotes.                                                           |
| `release version 25 not supported` | Maven is using an older JDK.   | Point `JAVA_HOME` at JDK 25, or add `-Djava.version=21`.                                |

## Project layout

``` tree
stations/020-bank-statement-pages/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tijori/statements/
│   ├── StatementController.java   ├── Page.java   ├── Accounts.java
│   ├── Transaction.java           └── StatementsApplication.java
├── src/test/java/com/tijori/statements/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/tijori/statements/StatementController.java`

Does  
Validates page and size, finds the account, refuses deep pages, and returns one page.

Why  
Limits are declared on the parameters (`@Min`, `@Max`), so the rule is visible where the request arrives.

Without it  
Any size, offset in `int`.

#### `src/main/java/com/tijori/statements/Page.java`

Does  
A generic page for any element type that has an id.

Why  
`T extends Identified` lets the page name its last id; a plain `T` could not.

Without it  
A page class per element type.

- The offset is a `long`, so page × size cannot wrap around.
- `List.copyOf` keeps the page immutable.

#### `src/main/java/com/tijori/statements/Accounts.java`

Does  
The two demo accounts, generated from a fixed seed, kept in statement order.

Why  
One `Comparator` chain defines the order everywhere.

Without it  
Sorting by time only.

#### `src/main/java/com/tijori/statements/Transaction.java`

A statement line, as a record that is `Page.Identified`.

#### `src/main/resources/application.yaml`

Problem bodies for every error.

#### `src/main/java/com/tijori/statements/StatementsApplication.java`

Standard Spring Boot entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                             | Test class                   | Result |
|---------------|---------------------------------------------------------|------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                | `StatementContractTest` (5)  | pass   |
| Every station | Reproduce the failure before the fix                    | `BottomlessPageTrapTest` (3) | pass   |
| This station  | Every page walked at several sizes; tie order; generics | `PageTest` (4)               | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.statements.StatementContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.statements.BottomlessPageTrapTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.statements.PageTest
[INFO] Tests run: 12, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/tijori/statements/BottomlessPageTrapTest.java`

Written first: the old paging's 4,000 rows and its negative offset, and the fixed endpoint's 400s.

#### `src/test/java/com/tijori/statements/StatementContractTest.java`

First, last and past-the-end pages, the limits, and unknown accounts.

#### `src/test/java/com/tijori/statements/PageTest.java`

Walks every page at four sizes, checks the tie order, and uses `Page` with another type.

#### `src/test/java/com/tijori/statements/ApiTest.java`

Shared setup: the whole app through MockMvc and a request helper.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/tijori/statements/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=DateRangeChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 12 tests.

Checked (`docs/challenge-run.txt`): with the reference solution copied in, all 16 tests pass (12 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## A statement for a date range

Add optional `from` and `to` dates (inclusive). The page and its totals cover only that range; a backwards range is `400`.

**Done when:** both tests in `DateRangeChallengeTest` pass: September 2026 is 346 transactions over 4 pages of 100.

Hints

- `@DateTimeFormat(iso = DateTimeFormat.ISO.DATE)` parses `2026-09-01`; anything else is a `400` on its own.
- Filter first, then page: `Page.of` does not change.

#### `challenge/DateRangeChallengeTest.java`

``` code
package com.tijori.statements;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.everyItem;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.startsWith;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: optional from and to dates (inclusive). The page and its totals cover only that range,
 * the way a "statement for September" works.
 */
class DateRangeChallengeTest extends ApiTest {

    @Test
    void aMonthIsItsOwnSetOfPages() throws Exception {
        transactions("acc-1001", "from", "2026-09-01", "to", "2026-09-30", "size", "100")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.totalItems").value(346))
                .andExpect(jsonPath("$.totalPages").value(4))
                .andExpect(jsonPath("$.items[*].postedAt", everyItem(startsWith("2026-09"))));
        transactions("acc-1001", "from", "2026-09-15", "to", "2026-09-15")
                .andExpect(jsonPath("$.items", hasSize(16)))
                .andExpect(jsonPath("$.hasNext").value(false));
    }

    @Test
    void aBackwardsRangeIs400AndAnEmptyRangeIsEmpty() throws Exception {
        transactions("acc-1001", "from", "2026-09-30", "to", "2026-09-01").andExpect(status().isBadRequest());
        transactions("acc-1001", "from", "2024-01-01", "to", "2024-01-31").andExpect(jsonPath("$.totalItems").value(0));
        transactions("acc-1001", "from", "01-09-2026").andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 20 minutes

## Largest first

Add `sort=largest`: by the size of the amount, debit or credit, then the statement order. `sort=newest` stays the default; anything else is `400`.

**Done when:** both tests in `LargestFirstChallengeTest` pass.

Hints

- `Comparator.comparingLong(t -> Math.abs(t.amountPaise())).reversed()`, then `.thenComparing(Accounts.STATEMENT_ORDER)`.
- Without the last step, two equal amounts could swap between pages.

#### `challenge/LargestFirstChallengeTest.java`

``` code
package com.tijori.statements;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: sort=largest orders by the size of the amount (debit or credit), then newest first, then id:
 * a three-step Comparator chain. sort=newest is the default.
 */
class LargestFirstChallengeTest extends ApiTest {

    @Test
    void theLargestAmountsComeFirst() throws Exception {
        transactions("acc-1001", "sort", "largest", "size", "3")
                .andExpect(jsonPath("$.items[0].id").value(461))
                .andExpect(jsonPath("$.items[0].amountPaise").value(5_098_009))
                .andExpect(jsonPath("$.items[1].id").value(3064))
                .andExpect(jsonPath("$.items[2].id").value(1692))
                .andExpect(jsonPath("$.totalItems").value(4000));
    }

    @Test
    void newestIsTheDefaultAndAnUnknownSortIs400() throws Exception {
        transactions("acc-1001", "sort", "newest").andExpect(jsonPath("$.items[0].id").value(3998));
        transactions("acc-1001", "sort", "cheapest").andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## A new transaction arrives between two pages

Asha reads page 0 (the newest 20). A new UPI payment is posted. She asks for page 1. Which transaction does she see twice? Draw the two pages. How would "the 20 transactions older than id 3979" (a cursor) avoid it, and what does the cursor need from the order?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the old paging's whole-history response and its `int` overflow.
2.  Write `Page<T extends Identified>` with a `long` offset; walk every page in a test.
3.  Define the statement order as one `Comparator` chain with a unique tie-breaker.
4.  Bound size and depth on the controller, with problem bodies that say the limit.

## Design alternatives and trade-offs

| Approach                              | What it costs                                                        | Verdict                          |
|---------------------------------------|----------------------------------------------------------------------|----------------------------------|
| Offset paging, bounded size and depth | Deep pages refused; drifts on live data.                             | Chosen here                      |
| Unbounded size                        | One request can load everything.                                     | Wrong                            |
| Silently clamp size to 100            | No error, but the client gets less than it asked and may not notice. | Possible; say so in the response |
| Keyset (cursor) paging                | No jump to page 40; stable on live data and fast at any depth.       | Station 66                       |
| Spring Data `Page`/`Pageable`         | Ready-made with a database; this station builds the idea by hand.    | With JPA or JDBC repositories    |

## Database design

None in this station. With a database: an index on `(account_id, posted_at DESC, id DESC)` matches the order exactly, so each page is an index range. `OFFSET 9900` still walks 9,900 index entries, which is why the depth is capped.

# 3 · Go deeper: Production

Limits  
Every list endpoint gets a maximum size, documented and enforced on the server. The client can ask for less, never more.

Counting  
`totalItems` is cheap here. On a large table, `COUNT(*)` on every page request costs as much as the page; many APIs drop it or cache it.

Live data  
New transactions shift every offset by one. Statements for closed periods are stable; the live feed needs a cursor.

Mobile  
Twenty rows a page keeps responses small on slow networks; the app loads more as the user scrolls.

# 3 · Go deeper: Interview

## Interview takeaways

Why must page size be bounded?

Otherwise one request decides how much memory, database time and bandwidth the server spends. A maximum turns a possible outage into a 400.

What is wrong with deep offsets?

The database still reads and discards every skipped row, so page 10,000 is slow; and on live data, inserts shift the rows between requests.

Why does the order need a tie-breaker?

Without a unique last key, rows with equal values have no defined order, and the same row can appear on two pages or none.

What is a bounded type parameter for?

To use something from the element type inside generic code. Page\<T extends Identified\> can read item ids; Page\<T\> could not.

How can page × size go wrong in Java?

Two ints multiply as an int. 200,000,000 × 20 wraps to a negative number. Cast one side to long first.

## Self-check rubric

| Area        | Meets the bar                               | Above the bar                                     |
|-------------|---------------------------------------------|---------------------------------------------------|
| Correctness | All 12 tests pass.                          | You can predict `totalPages` for any size.        |
| Limits      | Size and depth are bounded with clear 400s. | You can explain the cost of OFFSET in a database. |
| Generics    | `Page<T>` works for another type.           | You can say why the bound is there.               |
| Explanation | Why the order needs a tie-breaker.          | Offset versus cursor paging on live data.         |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any list endpoint:

- Is there a maximum page size, enforced on the server?
- Is the order total, with a unique last key?
- Can page × size overflow, or reach a depth the database cannot serve quickly?
- What does a client see past the last page?
