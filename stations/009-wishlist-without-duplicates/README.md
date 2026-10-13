# Station 009 · Wishlist without duplicates

Foundations · 0–1 years · Core · E-commerce · Types: none

Spring Boot 4.1.1 · Java 25 · Spring MVC · Java records · HashSet / HashMap · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Five products and two wishlists (7 and 8) are fixed in the code; wishlists live in memory. No login: the wishlist id is in the URL.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 14 tests.

# 1 · Understand

## The problem in real life

1.  **Ravi wishes for a phone three times**

    He taps the heart on the search page, the product page and an old version of the app. Each sends the SKU slightly differently: `ph-12`, `PH-12`, `␠PH-12␠`.

2.  **The wishlist shows the phone three times**

    The server's SKU class compared case-insensitively in `equals` but never defined `hashCode`, so the `HashSet` put each copy in a different bucket and never compared them.

3.  **The fix**

    A record `Sku` that normalises in its constructor: every spelling becomes `PH-12` before it is stored, and records give matching `equals` and `hashCode`.

A `HashSet` asks two questions: "which bucket?" (`hashCode`) and then "same thing?" (`equals`). If the answers disagree, duplicates get in.

## What are we building?

A wishlist API: add a product by SKU, read the wishlist, remove a product. However a SKU is spelled, it is in the list once, and the list keeps the order products were added.

## An everyday analogy

A library shelves books by the first letter of the title. A librarian checks for duplicates only on the shelf where a book belongs. If the shelving rule says "first letter" but the duplicate rule says "same book in any case", then "the hobbit" (shelf t) and "The Hobbit" (shelf T) are never compared, and the library ends up with two. The shelving rule (`hashCode`) must agree with the duplicate rule (`equals`).

## How it works in 4 steps

1.  **The app sends a SKU** in any spelling: `{"sku": " ph-12 "}`.
2.  **The `Sku` record normalises it** to `PH-12` (or refuses a malformed one with `400`).
3.  **The catalogue is checked**: an unknown product is `422`.
4.  **The wishlist set adds it**: `201` if new, `200` if it was already there. Either way, once.

Check yourself: a key in a HashSet changes its value after being added. Why can the set no longer find it?

The set put it in the bucket for its *old* hashCode. Looking it up now computes the *new* hashCode and searches a different bucket. The object is still in the set but cannot be found or removed. That is why keys must be immutable.

## What this station is not

- **No login and no database.** Two wishlists live in memory.
- **No prices that change.** The catalogue is fixed.

## Key terms

| Term                  | Simple meaning                                                                            | Everyday example                                                            | In this project                                             |
|-----------------------|-------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------|-------------------------------------------------------------|
| **SKU**               | A product's code.                                                                         | The number printed under a barcode.                                         | `PH-12`                                                     |
| **`equals`**          | Java's question "are these two objects the same thing?"                                   | Two printed copies of the same ticket.                                      | `Sku("ph-12")` equals `Sku("PH-12")`.                       |
| **`hashCode`**        | A number that says which bucket an object goes in. Equal objects must have equal numbers. | The shelf number in a library: the same book always goes to the same shelf. | Comes free with a record.                                   |
| **HashSet / HashMap** | Collections that find things fast by bucket, then confirm with `equals`.                  | Going straight to shelf 42, then reading the titles there.                  | A wishlist is a set of SKUs; the catalogue is a map by SKU. |
| **Record**            | A Java class that only holds data; equals, hashCode and toString come from its fields.    | A filled-in form: two forms with the same entries are the same.             | `record Sku(String value)`                                  |
| **Immutable key**     | A key that cannot change after it is created.                                             | A house number painted in, not chalked.                                     | Records have no setters.                                    |
| **Normalise**         | Bring values to one standard form before comparing.                                       | Writing every name in capitals.                                             | Trimmed and upper-cased in the `Sku` constructor.           |

# 2 · Build: Spec

## Business problem

**Kartwala** (the marketplace from station 003) sends price-drop alerts to wishlist owners. Some customers got the same alert three times, because the same phone was in their wishlist three times. The SKU arrives in different spellings from different screens and app versions, and the server's SKU class broke the `equals`/`hashCode` contract.

## Acceptance criteria

1.  **Given** an empty wishlist, **when** `ph-12`, `PH-12` and `␠PH-12␠` are added, **then** the wishlist holds `PH-12` once: `201`, then `200`, `200`.
2.  **Given** several products, **then** they are listed in the order first added; adding one again does not move it.
3.  **Given** a DELETE in any letter case, **then** `204`, and again `204`.
4.  **Given** a malformed SKU, **then** `400` without echoing it. **Given** an unknown product, **then** `422`. **Given** an unknown wishlist, **then** `404`.

## Requirements

- A SKU is 2–30 letters, digits or hyphens, starting with a letter or digit; compared after trimming and upper-casing with `Locale.ROOT`.
- Equal SKUs must have equal hash codes; SKUs never change after creation.
- Each wishlist is a set that keeps insertion order.
- Errors are RFC 9457 problems that never repeat input.

## Learning objectives

- State the `equals`/`hashCode` contract and show what breaks without it.
- Use records for value equality and immutable keys.
- Normalise in the constructor, so no unnormalised value exists.
- Choose `HashSet`, `LinkedHashSet` or `HashMap` for the job.
- Use the boolean from `Set.add` instead of a separate `contains` check.

# 2 · Build: API contract

## Endpoints

| Method   | Path                          | Purpose                                                                    |
|----------|-------------------------------|----------------------------------------------------------------------------|
| `GET`    | `/wishlists/{id}`             | The wishlist: `wishlistId`, `count`, `items` (sku, name, pricePaise)       |
| `POST`   | `/wishlists/{id}/items`       | Add a product: `{"sku": "PH-12"}`. `201` if added, `200` if already there. |
| `DELETE` | `/wishlists/{id}/items/{sku}` | Remove a product: `204`, even if it was not there.                         |

## Status codes

| Status | When                                                       |
|--------|------------------------------------------------------------|
| 201    | The product was added                                      |
| 200    | The product was already in the list (in any spelling); GET |
| 204    | Removed (or was not there)                                 |
| 400    | Missing or malformed SKU                                   |
| 404    | Unknown wishlist                                           |
| 422    | Well-formed SKU that is not in the catalogue               |

Why POST here, after station 008 said POST is not idempotent? Adding to a *set* is idempotent in effect: the second add changes nothing. The different status (`201` then `200`) tells the app whether this request added it.

## Captured examples

Captured with curl from the running app on 13 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: the search page adds "ph-12"

**Why:** new to this wishlist: `201`, stored as `PH-12`.

Request

``` code
POST /wishlists/7/items HTTP/1.1
Content-Type: application/json

{
  "sku": "ph-12"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json

{
  "wishlistId": 7,
  "count": 1,
  "items": [
    {
      "sku": "PH-12",
      "name": "Samsung Galaxy M35 5G",
      "pricePaise": 1699900
    }
  ]
}
```

### Case 2: the product page adds "PH-12"

**Why:** the same SKU, so the set does not change: `200`, count still 1.

Request

``` code
POST /wishlists/7/items HTTP/1.1
Content-Type: application/json

{
  "sku": "PH-12"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json

{
  "wishlistId": 7,
  "count": 1,
  "items": [
    {
      "sku": "PH-12",
      "name": "Samsung Galaxy M35 5G",
      "pricePaise": 1699900
    }
  ]
}
```

### Case 3: an old app adds " PH-12 "

**Why:** trimmed in the constructor before any comparison: still the same SKU.

Request

``` code
POST /wishlists/7/items HTTP/1.1
Content-Type: application/json

{
  "sku": " PH-12 "
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json

{
  "wishlistId": 7,
  "count": 1,
  "items": [
    {
      "sku": "PH-12",
      "name": "Samsung Galaxy M35 5G",
      "pricePaise": 1699900
    }
  ]
}
```

### Case 4: a second product

**Why:** a different SKU: `201`, added after the phone.

Request

``` code
POST /wishlists/7/items HTTP/1.1
Content-Type: application/json

{
  "sku": "tv-55"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json

{
  "wishlistId": 7,
  "count": 2,
  "items": [
    {
      "sku": "PH-12",
      "name": "Samsung Galaxy M35 5G",
      "pricePaise": 1699900
    },
    {
      "sku": "TV-55",
      "name": "Samsung 55-inch Crystal TV",
      "pricePaise": 4299000
    }
  ]
}
```

### Case 5: a SKU not in the catalogue

**Why:** well-formed but no such product: `422`.

Request

``` code
POST /wishlists/7/items HTTP/1.1
Content-Type: application/json

{
  "sku": "XX-99"
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "No product has this SKU.",
  "instance": "/wishlists/7/items",
  "status": 422,
  "title": "Unknown product"
}
```

### Case 6: a malformed SKU

**Why:** spaces and `!` are not allowed: `400` with a fixed message, not the input.

Request

``` code
POST /wishlists/7/items HTTP/1.1
Content-Type: application/json

{
  "sku": "PH 12!"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "A SKU is 2-30 letters, digits or hyphens, like PH-12.",
  "instance": "/wishlists/7/items",
  "status": 400,
  "title": "Invalid SKU"
}
```

### Case 7: remove in lower case

**Why:** `ph-12` becomes `PH-12` and is removed: `204`.

Request

``` code
DELETE /wishlists/7/items/ph-12 HTTP/1.1
```

Response

``` code
HTTP/1.1 204
```

### Case 8: what is left

**Why:** only the TV.

Request

``` code
GET /wishlists/7 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 109

{
  "wishlistId": 7,
  "count": 1,
  "items": [
    {
      "sku": "TV-55",
      "name": "Samsung 55-inch Crystal TV",
      "pricePaise": 4299000
    }
  ]
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                               | What happens                                    | Proved by                                   |
|--------------------------------------------------------------------|-------------------------------------------------|---------------------------------------------|
| Three spellings of one SKU                                         | Stored once                                     | `theRealWishlistKeepsOnePhone`              |
| Equal SKUs                                                         | Equal hash codes; not equal to a String or null | `equalSkusHaveEqualHashCodes`               |
| As keys in HashSet and HashMap                                     | One key per SKU                                 | `aHashSetAndAHashMapTreatThemAsOneKey`      |
| Turkish server locale                                              | `mi-11x` still equals `MI-11X`                  | `aTurkishServerLocaleDoesNotChangeTheKey`   |
| Empty, one letter, space or underscore inside, 31 characters, null | Refused                                         | `malformedValuesAreRefused`                 |
| Order                                                              | First-added order; re-adding does not move it   | `itemsKeepTheOrderTheyWereAdded`            |
| Two wishlists                                                      | Independent                                     | `wishlistsAreSeparate`                      |
| Remove in another case; remove again                               | `204`, `204`                                    | `removingIs204InAnyLetterCaseAndAgainIs204` |
| Malformed SKU, blank, missing field                                | `400`, not echoed                               | `aMalformedSkuIs400WithoutEchoingIt`        |
| Unknown product                                                    | `422`                                           | `aWellFormedSkuThatIsNotInTheCatalogIs422`  |
| Unknown wishlist                                                   | `404`                                           | `anUnknownWishlistIs404`                    |

## The trap

Plausible but wrong

Overriding `equals` without `hashCode`, or using a mutable field as the key.

The "before" `OldSku` has a careful `equals`, and a unit test comparing two of them with `equals` passes. But a `HashSet` uses `hashCode` first, and `Object.hashCode` gives each object its own number, so the three spellings are never compared. The first test shows three phones; the second shows a mutable key getting lost inside a set; the third shows the real API keeping one phone. Removing the upper-casing from `Sku` was tried while building: 7 tests went red.

``` code
package com.kartwala.wishlist;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: it reproduces the bug before the fix.
 * The same phone arrives as "ph-12" (search page), "PH-12" (product page) and " PH-12 " (an old app).
 */
@Import(EqualsWithoutHashCodeTrapTest.OldWishlistController.class)
class EqualsWithoutHashCodeTrapTest extends ApiTest {

    /** The "before" key: equals ignores case and spaces, but hashCode was never overridden. */
    static final class OldSku {
        final String value;

        OldSku(String value) {
            this.value = value;
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof OldSku other && value.strip().equalsIgnoreCase(other.value.strip());
        }
        // no hashCode(): Object's version gives each object its own number, so HashSet never even calls equals
    }

    /** A key someone can change after it went into the set. */
    static final class MutableSku {
        String value;

        MutableSku(String value) {
            this.value = value;
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof MutableSku other && value.equals(other.value);
        }

        @Override
        public int hashCode() {
            return value.hashCode();
        }
    }

    @RestController
    static class OldWishlistController {
        private final Set<OldSku> items = new HashSet<>();

        @PostMapping("/old/wishlists/7/items")
        synchronized void add(@RequestBody Map<String, String> body) {
            items.add(new OldSku(body.get("sku")));
        }

        @GetMapping("/old/wishlists/7")
        synchronized Object get() {
            return items.stream().map(s -> s.value).toList();
        }
    }

    @Test
    void equalsWithoutHashCodeLetsTheSamePhoneInThreeTimes() throws Exception {
        for (String sku : new String[]{"ph-12", "PH-12", " PH-12 "}) {
            mvc.perform(post("/old/wishlists/7/items").contentType("application/json").content("{\"sku\":\"" + sku + "\"}"))
                    .andExpect(status().isOk());
        }
        mvc.perform(get("/old/wishlists/7")).andExpect(jsonPath("$", hasSize(3))); // the bug from the support ticket
    }

    @Test
    void aKeyChangedAfterInsertionIsLostInsideTheSet() {
        Set<MutableSku> set = new HashSet<>();
        MutableSku phone = new MutableSku("PH-12");
        set.add(phone);
        phone.value = "PH-13";                                    // someone "fixes" the SKU in place
        assertThat(set).hasSize(1);
        assertThat(set.contains(new MutableSku("PH-13"))).isFalse(); // stored in PH-12's bucket, looked up in PH-13's
        assertThat(set.remove(phone)).isFalse();                  // and it cannot even be removed
    }

    @Test
    void theRealWishlistKeepsOnePhone() throws Exception {
        add(7, "ph-12").andExpect(status().isCreated());
        add(7, "PH-12").andExpect(status().isOk());
        add(7, " PH-12 ").andExpect(status().isOk());
        mvc.perform(get("/wishlists/7")).andExpect(jsonPath("$.count").value(1)).andExpect(jsonPath("$.items[0].sku").value("PH-12"));
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
./mvnw test                 # all 14 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

The bodies are in `docs/sku-lower.json` (`ph-12`) and `docs/sku-upper.json` (`PH-12`).

``` code
# Add twice in two spellings: expect 201, then 200
curl -i -X POST http://localhost:8080/wishlists/7/items -H "Content-Type: application/json" -d "@docs/sku-lower.json"
curl -i -X POST http://localhost:8080/wishlists/7/items -H "Content-Type: application/json" -d "@docs/sku-upper.json"

# One phone: "count": 1
curl http://localhost:8080/wishlists/7
```

## Troubleshooting

| You see                            | Cause                                        | Fix                                                      |
|------------------------------------|----------------------------------------------|----------------------------------------------------------|
| `422 Unknown product`              | The SKU is not one of the five in `Catalog`. | Use PH-12, TV-55, EB-141, MI-11X or CK-5L.               |
| `404`                              | Only wishlists 7 and 8 exist.                | Use one of those ids.                                    |
| `release version 25 not supported` | Maven is using an older JDK.                 | Point `JAVA_HOME` at JDK 25, or add `-Djava.version=21`. |

## Project layout

``` tree
stations/009-wishlist-without-duplicates/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/kartwala/wishlist/
│   ├── WishlistController.java   ├── Sku.java        ├── Wishlists.java
│   ├── Catalog.java              ├── ApiErrors.java  └── WishlistApplication.java
├── src/test/java/com/kartwala/wishlist/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/kartwala/wishlist/WishlistController.java`

Does  
Three endpoints. Turns raw text into a `Sku` (or `400`), checks the catalogue (`422`), adds, and answers `201` or `200`.

Why  
All HTTP decisions in one place.

Without it  
No API.

- `wishlists.add` returns whether the set changed, which picks the status: no separate `contains` check that could race.

#### `src/main/java/com/kartwala/wishlist/Sku.java`

Does  
The key: one normalised, validated, immutable value.

Why  
A record gives `equals` and `hashCode` from the same field, so they always agree; normalising in the constructor means no unnormalised SKU can exist.

Without it  
Every caller would have to remember to trim and upper-case, and one would forget.

#### `src/main/java/com/kartwala/wishlist/Wishlists.java`

Does  
Holds a `LinkedHashSet<Sku>` per wishlist.

Why  
A set refuses duplicates by itself; "linked" keeps the order they were added.

Without it  
A list, where duplicates need manual checks.

#### `src/main/java/com/kartwala/wishlist/Catalog.java`

Does  
The products, in a `Map<Sku, Product>`.

Why  
Shows a record used as a map key: lookups by an equal Sku find the product.

Without it  
No names or prices in the wishlist.

#### `src/main/java/com/kartwala/wishlist/ApiErrors.java`

Adds an `errors` map to validation failures (as in station 004).

#### `src/main/java/com/kartwala/wishlist/WishlistApplication.java`

Standard Spring Boot entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                              | Test class                          | Result |
|---------------|------------------------------------------|-------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found | `WishlistContractTest` (7)          | pass   |
| Every station | Reproduce the failure before the fix     | `EqualsWithoutHashCodeTrapTest` (3) | pass   |
| This station  | The equals/hashCode contract on the key  | `SkuTest` (4)                       | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.wishlist.SkuTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.wishlist.EqualsWithoutHashCodeTrapTest
[INFO] Tests run: 7, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.wishlist.WishlistContractTest
[INFO] Tests run: 14, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/kartwala/wishlist/EqualsWithoutHashCodeTrapTest.java`

Written first: three phones from a broken key; a lost mutable key; one phone with the record.

#### `src/test/java/com/kartwala/wishlist/SkuTest.java`

The contract checked pair by pair, sets and maps, a Turkish locale, refused values.

#### `src/test/java/com/kartwala/wishlist/WishlistContractTest.java`

Add, order, separate lists, remove twice, every refusal.

#### `src/test/java/com/kartwala/wishlist/ApiTest.java`

Shared setup: the whole app through MockMvc, empty wishlists before each test.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/kartwala/wishlist/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=MergeGuestWishlistChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 14 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 19 tests pass (14 station tests and 5 challenge tests).

Challenge 1 · Beginner-friendly · about 30 minutes

## Merge a guest wishlist

A guest's hearts must join their wishlist when they sign in. Add `POST /wishlists/{id}/merge` with `{"skus": [...]}`: existing items stay first, new ones follow in the order sent, duplicates in any spelling are skipped, and one bad or unknown SKU means nothing is merged.

**Done when:** all three tests in `MergeGuestWishlistChallengeTest` pass, and the station's tests still pass.

Hints

- Turn every string into a `Sku` and check the catalogue before changing anything: all or nothing.
- `Set.addAll` skips what is already there, and a `LinkedHashSet` appends the rest in order.

#### `challenge/MergeGuestWishlistChallengeTest.java`

``` code
package com.kartwala.wishlist;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: a guest's wishlist is merged into the customer's when they sign in. No duplicates, all or nothing. */
class MergeGuestWishlistChallengeTest extends ApiTest {

    ResultActions merge(String skusJson) throws Exception {
        return mvc.perform(post("/wishlists/7/merge").contentType(MediaType.APPLICATION_JSON).content("{\"skus\":" + skusJson + "}"));
    }

    @Test
    void mergeKeepsExistingItemsFirstAndAddsOnlyNewOnes() throws Exception {
        add(7, "PH-12");
        merge("[\"ph-12\", \"TV-55\", \" tv-55 \", \"eb-141\"]")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items[*].sku", contains("PH-12", "TV-55", "EB-141")));
    }

    @Test
    void oneBadSkuMeansNothingIsMerged() throws Exception {
        add(7, "PH-12");
        merge("[\"TV-55\", \"bad sku\"]").andExpect(status().isBadRequest());
        merge("[\"TV-55\", \"XX-99\"]").andExpect(status().isUnprocessableContent());
        mvc.perform(get("/wishlists/7")).andExpect(jsonPath("$.items[*].sku", contains("PH-12")));
    }

    @Test
    void mergingTheSameListTwiceChangesNothingTheSecondTime() throws Exception {
        merge("[\"TV-55\", \"CK-5L\"]");
        merge("[\"TV-55\", \"CK-5L\"]").andExpect(jsonPath("$.count").value(2));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Beginner-friendly · about 30 minutes

## Most-wished products

Merchandising wants `GET /products/most-wished?limit=10`: each product with how many wishlists hold it, most first, ties by SKU.

**Done when:** both tests in `MostWishedChallengeTest` pass.

Hints

- Count in a `HashMap<Sku, Integer>` with `merge(sku, 1, Integer::sum)`: this works only because `Sku` has value equality.
- Sort entries by value descending, then by key; then `limit`.

#### `challenge/MostWishedChallengeTest.java`

``` code
package com.kartwala.wishlist;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: GET /products/most-wished: how many wishlists hold each product, most first. */
class MostWishedChallengeTest extends ApiTest {

    @Test
    void productsAreCountedOncePerWishlistAndRanked() throws Exception {
        add(7, "PH-12");
        add(7, "ph-12");   // same wishlist again: still one
        add(7, "TV-55");
        add(8, "PH-12");
        add(8, "EB-141");
        mvc.perform(get("/products/most-wished").param("limit", "2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[*].sku", contains("PH-12", "EB-141")))   // ties ordered by SKU
                .andExpect(jsonPath("$[0].wishlists").value(2))
                .andExpect(jsonPath("$[1].wishlists").value(1));
    }

    @Test
    void nothingWishedIsAnEmptyList() throws Exception {
        mvc.perform(get("/products/most-wished")).andExpect(status().isOk()).andExpect(jsonPath("$").isEmpty());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Same product, two SKUs

Kartwala's sellers list the same phone under different SKUs (`PH-12` from one seller, `SAM-M35-BLK` from another). Customers want it once in their wishlist. Is that an equality problem or a data problem? Where would you keep the link between the SKUs, and what would the wishlist store?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: equals without hashCode lets three phones in.
2.  Make `Sku` a record that normalises and validates in its constructor.
3.  Store each wishlist as a `LinkedHashSet<Sku>`; use `add`'s boolean for the status.
4.  Test the contract pair by pair, and in real sets and maps.

## Design alternatives and trade-offs

| Approach                                                     | What it costs                                                                                         | Verdict    |
|--------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|------------|
| Record that normalises in its constructor                    | Nothing; the canonical value is all that exists.                                                      | Chosen     |
| Class with case-insensitive `equals` and no `hashCode`       | Duplicates in every hash collection (the trap).                                                       | Wrong      |
| Class with matching case-insensitive `equals` and `hashCode` | Works, but every method must remember the rule, and the response shows whichever spelling came first. | Possible   |
| `TreeSet` with `String.CASE_INSENSITIVE_ORDER`               | Uses a comparator instead of equals; loses insertion order; ignores spaces only if you trim first.    | Possible   |
| Lombok `@EqualsAndHashCode`                                  | Generated and consistent, but a dependency for what records already do.                               | Not needed |

## Database design

None in this station. With a database, the same rule is a primary key `(wishlist_id, sku)` plus a check that `sku = upper(trim(sku))`, so a script cannot insert a second spelling.

# 3 · Go deeper: Production

Correctness  
Every place that compares SKUs gets the same answer, because there is one normalised form. Price-drop alerts go out once per product.

Performance  
Hash lookups take constant time on average. A broken `hashCode` that returns the same number for everything is "correct" but turns every set into a slow list.

Security  
The wishlist id in the URL is a demo shortcut; real apps take it from the login. A malformed SKU is refused with a fixed message.

Maintainability  
Changing the SKU rule (say, allowing dots) is one pattern in one record.

# 3 · Go deeper: Interview

## Interview takeaways

What is the equals/hashCode contract?

If two objects are equal by equals, they must have the same hashCode. (Equal hash codes do not have to mean equal objects.) Hash collections rely on it: they find the bucket with hashCode, then compare with equals.

What happens if you override equals but not hashCode?

Equal objects get different hash codes (Object's version), land in different buckets, and are never compared. HashSet keeps duplicates; HashMap lookups by an equal key return null.

Why must map keys be immutable?

The bucket is chosen when the key is inserted. If the key's fields change, its hashCode changes, and lookups search the wrong bucket: the entry is still there but cannot be found or removed.

What do records give you?

A constructor, accessors, and equals, hashCode and toString based on all components. Fields are final, so records make good keys, as long as their components are immutable too.

Why normalise in the constructor rather than in equals?

Then only canonical values exist: equals, hashCode, toString, JSON output and database storage all see the same form, with no rule repeated.

## Self-check rubric

| Area        | Meets the bar                               | Above the bar                                              |
|-------------|---------------------------------------------|------------------------------------------------------------|
| Correctness | All 14 tests pass.                          | You can predict which tests fail without the upper-casing. |
| Design      | A record key that normalises itself.        | You can compare it with a comparator-based TreeSet.        |
| Tests       | The contract is tested on real collections. | You showed a mutable key getting lost, in your own words.  |
| Explanation | You can state the contract.                 | You can explain buckets to someone new.                    |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any class you see used as a key:

- If it overrides `equals`, does it override `hashCode` with the same fields?
- Can any field used in them change after construction?
- Is the value normalised before it is compared, in one place?
- Would a record do the same job with less code?
