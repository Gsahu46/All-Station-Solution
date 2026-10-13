# Station 008 · Saved delivery addresses

Foundations · 0–1 years · Core · Food delivery · Types: Idempotency

Spring Boot 4.1.1 · Java 25 · Spring MVC · Bean Validation · JSON Merge Patch · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Two customers (42 and 43) are fixed in the code; addresses live in memory. No login: the customer id is in the URL.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 19 tests.

# 1 · Understand

## The problem in real life

1.  **Priya edits her home address**

    She is on a weak signal in a lift. She taps Save; the server saves it, but the reply never reaches her phone.

2.  **The app tries again**

    The old API used `POST`, which means "add one more". The retry adds a second "home". At checkout she sees two, and later deleting one shows an error because the other was already gone.

3.  **The fix**

    Name the address in the URL and use methods that are safe to repeat: `PUT …/addresses/home` sets it, `DELETE` removes it. Doing either twice leaves the same result.

Phones retry. The question is not whether a request arrives twice, but whether arriving twice does any harm.

## What are we building?

A saved-addresses API where each address is named by a label in the URL (`home`, `work`). `PUT` sets a whole address, `PATCH` changes some fields, `DELETE` removes it. Repeating any of them is harmless.

## An everyday analogy

A row of labelled letterboxes. "Put this letter in box HOME" twice leaves one letter in HOME, because the second replaces the first. "Drop a letter in the post box" twice sends two letters. `PUT` is the labelled box; `POST` is the post box.

## How it works in 4 steps

1.  **The label is in the URL**: `/customers/42/addresses/home`. Every request is about that one address.
2.  **PUT** stores the whole address under the label: `201` if new, `200` if replaced. Twice: still one address.
3.  **PATCH** changes only the fields sent; `null` removes an optional field. Twice: same result.
4.  **DELETE** makes sure the address is gone: `204` every time, even if it was already gone.

Check yourself: Priya's DELETE succeeds, but the reply is lost. The app sends DELETE again. What should it get?

`204` again. The goal "home is not saved" is already true, so the retry succeeds without doing anything. If the second DELETE returned an error, the app would show an error screen for something that worked.

## What this station is not

- **No login.** The customer id is in the URL; real apps take it from the signed-in user.
- **No database.** Addresses live in memory.
- **No protection against two phones editing at once.** The last save wins; Practice challenge 1 adds the fix.

## Key terms

| Term                 | Simple meaning                                                                        | Everyday example                                          | In this project                       |
|----------------------|---------------------------------------------------------------------------------------|-----------------------------------------------------------|---------------------------------------|
| **Idempotent**       | Doing it twice leaves things the same as doing it once.                               | Switching a light ON: pressing ON again changes nothing.  | PUT, PATCH (as used here) and DELETE. |
| **PUT**              | "Make the thing at this address exactly this."                                        | Replacing a whole page in a file.                         | `PUT /customers/42/addresses/home`    |
| **PATCH**            | "Change only these parts."                                                            | Correcting one word on the page.                          | `{"landmark": "Gate 2"}`              |
| **POST**             | "Add one more." Not idempotent: twice adds two.                                       | Dropping a letter in a post box.                          | Not allowed on an address here.       |
| **JSON Merge Patch** | A PATCH format (RFC 7396): fields present replace, `null` removes, missing ones stay. | A correction slip: cross out, write over, leave the rest. | `{"line2": null}` removes line 2.     |
| **204 No Content**   | "Done, nothing to send back."                                                         | A nod.                                                    | Every DELETE.                         |
| **405 + Allow**      | "That method is not allowed here; these are."                                         | A sign: "Entry only from the other door."                 | `POST` on an address.                 |

# 2 · Build: Spec

## Business problem

**Tiffino** (the food-delivery app from station 002) lets customers save delivery addresses. The API saves every edit with `POST /customers/{id}/addresses`, which adds a new entry. On flaky mobile networks the app retries, so customers end up with two or three copies of "home", and riders sometimes go to an old one. Deleting a duplicate a second time shows an error screen. Support tickets about "wrong address" are the top complaint in Bengaluru.

## Acceptance criteria

1.  **Given** a new label, **when** the app PUTs an address, **then** `201` with `Location`. **When** it PUTs the same again, **then** `200`, the same body, and still one address.
2.  **Given** a saved address, **when** the app PUTs a different address, **then** it replaces the whole address: fields left out are gone.
3.  **Given** a PATCH, **then** only the fields sent change; `null` removes an optional field; removing a required field is `400` and changes nothing.
4.  **Given** a DELETE, **then** `204`, and a second DELETE is `204` too.
5.  **Given** a POST to an address, **then** `405` with an `Allow` header listing GET, PUT, PATCH and DELETE.
6.  **Given** 10 saved addresses, **when** an 11th label is PUT, **then** `409`; replacing an existing one still works.

## Requirements

- Labels: 1–20 lower-case letters, digits or hyphens; `HOME` and `home` are the same label (`Locale.ROOT`).
- Address fields: `line1`, `city`, `pincode` (6 digits, not starting with 0) required; `line2`, `landmark` optional.
- PATCH uses JSON Merge Patch (`application/merge-patch+json`; plain JSON is accepted too). Only the five fields may be patched.
- No timestamps or counters in the stored address, so the same request always leaves exactly the same state.
- Errors are RFC 9457 problems that never repeat input.

## Learning objectives

- Choose between PUT, PATCH and POST, and explain which are idempotent.
- Design URLs so that a retry targets the same resource.
- Implement JSON Merge Patch, including `null` as "remove".
- Return `204` for DELETE, and `405` with `Allow`.
- Write replay tests: the same request twice gives one effect.

# 2 · Build: API contract

## Endpoints

| Method   | Path                                | Purpose                             | Idempotent?                     |
|----------|-------------------------------------|-------------------------------------|---------------------------------|
| `GET`    | `/customers/{id}/addresses`         | All saved addresses, by label       | Yes (and safe: changes nothing) |
| `GET`    | `/customers/{id}/addresses/{label}` | One address                         | Yes (safe)                      |
| `PUT`    | `/customers/{id}/addresses/{label}` | Create or replace the whole address | Yes                             |
| `PATCH`  | `/customers/{id}/addresses/{label}` | Change some fields (Merge Patch)    | Yes, for this kind of patch     |
| `DELETE` | `/customers/{id}/addresses/{label}` | Make sure it is gone                | Yes                             |
| `POST`   | `/customers/{id}/addresses/{label}` | Not supported: `405`                | (POST is not idempotent)        |

## Status codes

| Status | When                                                                                      |
|--------|-------------------------------------------------------------------------------------------|
| 201    | PUT created a new label; `Location` names it                                              |
| 200    | PUT replaced, PATCH changed, GET read                                                     |
| 204    | DELETE, whether or not the address existed                                                |
| 400    | Invalid label, field, or patch (unknown field, non-text value, removing a required field) |
| 404    | Unknown customer; GET or PATCH of a label with no address                                 |
| 405    | POST on an address; `Allow` lists the methods that work                                   |
| 409    | An 11th label                                                                             |

**Same state, not always the same status.** Idempotency (RFC 9110) is about the effect on the server. A repeated PUT answers `200` where the first answered `201`, and that is fine: the address is the same. This API also chose `204` for a repeated DELETE; returning `404` (as station 005 did) would also be idempotent, but it turns a successful retry into an error screen.

## Captured examples

Captured with curl from the running app on 13 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: save "home"

**Why:** no address had this label: `201`, and `Location` is the URL that was used.

Request

``` code
PUT /customers/42/addresses/home HTTP/1.1
Content-Type: application/json

{
  "line1": "Flat 402, Lotus Residency",
  "line2": "14th Cross, Indiranagar",
  "landmark": "Opposite Cafe Coffee Day",
  "city": "Bengaluru",
  "pincode": "560038"
}
```

Response

``` code
HTTP/1.1 201 
Location: /customers/42/addresses/home
Content-Type: application/json

{
  "line1": "Flat 402, Lotus Residency",
  "line2": "14th Cross, Indiranagar",
  "landmark": "Opposite Cafe Coffee Day",
  "city": "Bengaluru",
  "pincode": "560038"
}
```

### Case 2: the app's retry

**Why:** the same address under the same label: replaced by itself. `200`, same body, still one address.

Request

``` code
PUT /customers/42/addresses/home HTTP/1.1
Content-Type: application/json

{
  "line1": "Flat 402, Lotus Residency",
  "line2": "14th Cross, Indiranagar",
  "landmark": "Opposite Cafe Coffee Day",
  "city": "Bengaluru",
  "pincode": "560038"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json

{
  "line1": "Flat 402, Lotus Residency",
  "line2": "14th Cross, Indiranagar",
  "landmark": "Opposite Cafe Coffee Day",
  "city": "Bengaluru",
  "pincode": "560038"
}
```

### Case 3: change the landmark, remove line 2

**Why:** Merge Patch: `landmark` is replaced, `line2: null` removes it, everything else stays.

Request

``` code
PATCH /customers/42/addresses/home HTTP/1.1
Content-Type: application/merge-patch+json

{
  "landmark": "Next to Indiranagar metro",
  "line2": null
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 127

{
  "line1": "Flat 402, Lotus Residency",
  "line2": null,
  "landmark": "Next to Indiranagar metro",
  "city": "Bengaluru",
  "pincode": "560038"
}
```

### Case 4: all addresses

**Why:** one "home", whatever the retries did.

Request

``` code
GET /customers/42/addresses HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 136

{
  "home": {
    "line1": "Flat 402, Lotus Residency",
    "line2": null,
    "landmark": "Next to Indiranagar metro",
    "city": "Bengaluru",
    "pincode": "560038"
  }
}
```

### Case 5: an old app version POSTs

**Why:** POST would mean "add one more", which is the bug. `405`, and `Allow` tells the client what does work.

Request

``` code
POST /customers/42/addresses/home HTTP/1.1
Content-Type: application/json

{
  "line1": "Flat 402, Lotus Residency",
  "line2": "14th Cross, Indiranagar",
  "landmark": "Opposite Cafe Coffee Day",
  "city": "Bengaluru",
  "pincode": "560038"
}
```

Response

``` code
HTTP/1.1 405 
Allow: DELETE, PATCH, PUT, GET
Content-Type: application/problem+json

{
  "detail": "Method 'POST' is not supported.",
  "instance": "/customers/42/addresses/home",
  "status": 405,
  "title": "Method Not Allowed"
}
```

### Case 6: a 5-digit PIN code

**Why:** `400`, naming the field; nothing is saved.

Request

``` code
PUT /customers/42/addresses/work HTTP/1.1
Content-Type: application/json

{
  "line1": "Floor 3, Prestige Tech Park",
  "city": "Bengaluru",
  "pincode": "06003"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "The address has invalid fields.",
  "instance": "/customers/42/addresses/work",
  "status": 400,
  "title": "Bad Request",
  "errors": {
    "pincode": "must be a 6-digit PIN code"
  }
}
```

### Case 7: delete "home"

**Why:** `204`: gone, nothing to send back.

Request

``` code
DELETE /customers/42/addresses/home HTTP/1.1
```

Response

``` code
HTTP/1.1 204
```

### Case 8: the delete's retry

**Why:** already gone, so the goal is met: `204` again, no error screen.

Request

``` code
DELETE /customers/42/addresses/home HTTP/1.1
```

Response

``` code
HTTP/1.1 204
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                | What the API does                                     | Proved by                                                              |
|-----------------------------------------------------|-------------------------------------------------------|------------------------------------------------------------------------|
| Same PUT three times                                | One address; same body each time; `201`, `200`, `200` | `theSamePutThreeTimesLeavesOneIdenticalAddress`                        |
| Same PATCH twice                                    | Same state                                            | `theSamePatchTwiceLeavesTheSameAddress`                                |
| DELETE twice                                        | `204` both times                                      | `deletingTwiceIs204BothTimes`                                          |
| Retries on two labels                               | Each label independent                                | `retriesOfDifferentLabelsDoNotTouchEachOther`                          |
| PUT with fewer fields                               | Left-out fields are removed (PUT replaces)            | `putReplacesTheWholeAddressSoLeftOutFieldsAreGone`                     |
| `OFFICE` on a Turkish server                        | Same label as `office`                                | `labelsIgnoreLetterCaseEvenOnATurkishServer`                           |
| Bad label, PIN code starting with 0, blank line 1   | `400`                                                 | `anInvalidLabelOrBodyIs400`                                            |
| PATCH one field; `null` on an optional field        | Only that field changes / is removed                  | `patchChangesOnlyTheFieldsSent`, `patchWithNullRemovesAnOptionalField` |
| PATCH `city: null`                                  | `400`; nothing changes                                | `patchCannotRemoveARequiredFieldAndChangesNothing`                     |
| PATCH unknown field, an array, a number for pincode | `400`; the field name is not echoed                   | `patchWithAnUnknownFieldOrANonObjectIs400WithoutEchoingIt`             |
| PATCH a label with no address                       | `404`                                                 | `patchingAnAddressThatDoesNotExistIs404`                               |
| POST on an address                                  | `405` + `Allow`                                       | `postIs405AndTheAllowHeaderListsWhatWorks`                             |
| Unknown customer                                    | `404`                                                 | `anUnknownCustomerIs404`                                               |
| 11th label; replacing at the limit                  | `409`; `200`                                          | `theEleventhLabelIs409ButReplacingAnExistingOneStillWorks`             |

## The trap

Plausible but wrong

Using POST for edits, so a retry on a flaky network creates duplicates.

"Save address" feels like "create", so POST feels natural, and it works on office Wi-Fi. The first test sends the same POST twice, as an app does after a lost reply, to the "before" API: two addresses. The second sends the same PUT twice to the real API: one. Removing `Locale.ROOT` from the label was tried while building: the Turkish-locale test went red.

``` code
package com.tiffino.addresses;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.List;

import static org.hamcrest.Matchers.aMapWithSize;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: it reproduces the bug before the fix.
 * Priya edits her home address on a weak signal; the reply is lost, and the app sends the same request again.
 */
@Import(PostForEditsTrapTest.OldAddressController.class)
class PostForEditsTrapTest extends ApiTest {

    /** The "before" API: every save is a POST that adds an address to a list. Kept only in tests. */
    @RestController
    static class OldAddressController {
        private final List<Address> saved = new ArrayList<>();

        @PostMapping("/old/customers/{id}/addresses")
        synchronized Address save(@PathVariable long id, @RequestBody Address a) {
            saved.add(a);
            return a;
        }

        @GetMapping("/old/customers/{id}/addresses")
        synchronized List<Address> all(@PathVariable long id) {
            return List.copyOf(saved);
        }
    }

    @Test
    void aRetriedPostSavesTheSameAddressTwice() throws Exception {
        for (int attempt = 1; attempt <= 2; attempt++) { // attempt 1's reply was lost; attempt 2 is the app's retry
            mvc.perform(post("/old/customers/42/addresses").contentType(MediaType.APPLICATION_JSON).content(HOME))
                    .andExpect(status().isOk());
        }
        mvc.perform(get("/old/customers/42/addresses"))
                .andExpect(jsonPath("$", hasSize(2))); // the bug: two "home" addresses at checkout
    }

    @Test
    void aRetriedPutLeavesOneAddress() throws Exception {
        putAddress(42, "home", HOME).andExpect(status().isCreated());
        putAddress(42, "home", HOME).andExpect(status().isOk());
        mvc.perform(get("/customers/42/addresses")).andExpect(jsonPath("$", aMapWithSize(1)));
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

``` code
# Save twice: expect 201, then 200
curl -i -X PUT http://localhost:8080/customers/42/addresses/home -H "Content-Type: application/json" -d "@docs/address.json"
curl -i -X PUT http://localhost:8080/customers/42/addresses/home -H "Content-Type: application/json" -d "@docs/address.json"

# Patch: new landmark, no line 2
curl -i -X PATCH http://localhost:8080/customers/42/addresses/home -H "Content-Type: application/merge-patch+json" -d "@docs/patch.json"

# Still one address
curl http://localhost:8080/customers/42/addresses

# Delete twice: expect 204 both times
curl -i -X DELETE http://localhost:8080/customers/42/addresses/home
curl -i -X DELETE http://localhost:8080/customers/42/addresses/home
```

## Troubleshooting

| You see                            | Cause                            | Fix                                                       |
|------------------------------------|----------------------------------|-----------------------------------------------------------|
| `415` on PATCH                     | Missing or wrong `Content-Type`. | Use `application/merge-patch+json` or `application/json`. |
| `405`                              | POST instead of PUT.             | Addresses are set with PUT.                               |
| `release version 25 not supported` | Maven is using an older JDK.     | Point `JAVA_HOME` at JDK 25, or add `-Djava.version=21`.  |

## Project layout

``` tree
stations/008-saved-delivery-addresses/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tiffino/addresses/
│   ├── AddressController.java   ├── MergePatch.java   ├── AddressBook.java
│   ├── Address.java             ├── ApiErrors.java    └── AddressesApplication.java
├── src/test/java/com/tiffino/addresses/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     address.json, patch.json, capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/tiffino/addresses/AddressController.java`

Does  
Maps GET, PUT, PATCH and DELETE on `/customers/{id}/addresses/{label}`, normalises the label, and validates patched results.

Why  
The label in the URL makes every request target one known address, which is what makes retries safe.

Without it  
No API.

- No `@PostMapping`: Spring itself answers POST with `405` and `Allow`.
- A PATCH is validated *after* merging, because the rules apply to the result, not to the patch.

#### `src/main/java/com/tiffino/addresses/MergePatch.java`

Does  
Applies a JSON Merge Patch to an address: present replaces, `null` removes, missing stays.

Why  
One small, testable rule for partial updates.

Without it  
Clients would have to send the whole address to change one field, and two phones would overwrite each other's untouched fields.

- Error messages list the allowed fields instead of repeating the one sent.

#### `src/main/java/com/tiffino/addresses/AddressBook.java`

Does  
Keeps each customer's addresses in a map keyed by label.

Why  
A map cannot hold two "home" entries: putting again replaces.

Without it  
A list, where every save appends (the trap).

#### `src/main/java/com/tiffino/addresses/Address.java`

Does  
The address and its rules. Trims text; a blank optional field becomes `null`.

Why  
"" and a missing landmark are the same address, so retries with slightly different JSON still give the same state.

Without it  
Invalid addresses get saved.

#### `src/main/java/com/tiffino/addresses/ApiErrors.java`

Adds an `errors` map to validation failures (as in station 004).

#### `src/main/java/com/tiffino/addresses/AddressesApplication.java`

Standard Spring Boot entry point.

# 2 · Build: Tests

## Required tests for this station

Station type: Idempotency

| Required by   | Requirement                                     | Test class                 | Result |
|---------------|-------------------------------------------------|----------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found        | `AddressContractTest` (13) | pass   |
| Every station | Reproduce the failure before the fix            | `PostForEditsTrapTest` (2) | pass   |
| Idempotency   | Replay: the same request twice gives one effect | `AddressReplayTest` (4)    | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.addresses.AddressReplayTest
[INFO] Tests run: 13, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.addresses.AddressContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.addresses.PostForEditsTrapTest
[INFO] Tests run: 19, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/tiffino/addresses/PostForEditsTrapTest.java`

Written first: a retried POST makes two addresses; a retried PUT keeps one.

#### `src/test/java/com/tiffino/addresses/AddressReplayTest.java`

Each method repeated: the state after twice equals the state after once.

#### `src/test/java/com/tiffino/addresses/AddressContractTest.java`

Every method and status code, Merge Patch rules, `405` + `Allow`, the limit.

#### `src/test/java/com/tiffino/addresses/ApiTest.java`

Shared setup: the whole app through MockMvc, empty address books before each test.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/tiffino/addresses/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=ConditionalUpdateChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 19 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 27 tests pass (19 station tests and 8 challenge tests).

Challenge 1 · Go deeper · about 45 minutes

## Two phones, one address

Priya and her husband edit "home" on two phones. Today the last save silently wins. Return an `ETag` with GET, PUT and PATCH; when a save sends `If-Match` with an old ETag, refuse it with `412 Precondition Failed` and change nothing. Saves without `If-Match` keep working.

**Done when:** all four tests in `ConditionalUpdateChallengeTest` pass, and the station's tests still pass.

Hints

- The ETag is a fingerprint of the content: the same address must always give the same ETag.
- `ResponseEntity.ok().eTag(…)` sets the header, quotes included.
- Check and save in one step (`synchronized (book)`), or another save can slip in between.

#### `challenge/ConditionalUpdateChallengeTest.java`

``` code
package com.tiffino.addresses;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: Priya edits "home" on her phone while her husband edits it on his. Without a check, the second
 * save silently wipes out the first. With ETag and If-Match, the stale save is refused with 412.
 */
class ConditionalUpdateChallengeTest extends ApiTest {

    private String etag() throws Exception {
        return mvc.perform(get("/customers/42/addresses/home")).andExpect(header().exists("ETag"))
                .andReturn().getResponse().getHeader("ETag");
    }

    @Test
    void aSaveBasedOnAnOldVersionIs412AndChangesNothing() throws Exception {
        putAddress(42, "home", HOME);
        String seenByPriya = etag();
        patchAddress(42, "home", "{\"landmark\":\"Gate 2\"}");                     // her husband's phone saves first
        mvc.perform(put("/customers/42/addresses/home").header("If-Match", seenByPriya)
                        .contentType(MediaType.APPLICATION_JSON).content(HOME.replace("Flat 402", "Flat 403")))
                .andExpect(status().isPreconditionFailed())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
        mvc.perform(get("/customers/42/addresses/home")).andExpect(jsonPath("$.landmark").value("Gate 2"))
                .andExpect(jsonPath("$.line1").value("Flat 402, Lotus Residency"));
    }

    @Test
    void aSaveBasedOnTheCurrentVersionWorksAndReturnsTheNewETag() throws Exception {
        putAddress(42, "home", HOME);
        String current = etag();
        String next = mvc.perform(patch("/customers/42/addresses/home").header("If-Match", current)
                        .contentType("application/merge-patch+json").content("{\"landmark\":\"Gate 2\"}"))
                .andExpect(status().isOk())
                .andExpect(header().exists("ETag"))
                .andReturn().getResponse().getHeader("ETag");
        org.assertj.core.api.Assertions.assertThat(next).isNotEqualTo(current).isEqualTo(etag());
    }

    @Test
    void theSameAddressAlwaysHasTheSameETag() throws Exception {
        putAddress(42, "home", HOME);
        String first = etag();
        putAddress(42, "home", HOME);
        org.assertj.core.api.Assertions.assertThat(etag()).isEqualTo(first);
    }

    @Test
    void withoutIfMatchSavesStillWork() throws Exception {
        putAddress(42, "home", HOME).andExpect(status().isCreated());
        putAddress(42, "home", HOME).andExpect(status().isOk());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Beginner-friendly · about 30 minutes

## The default address

Add `PUT /customers/{id}/default-address` with `{"label": "home"}` and `GET` for it. There is one default at a time; setting it twice gives the same answer; a label with no address is `409`; deleting the default address clears it (`404` on GET).

**Done when:** all four tests in `DefaultAddressChallengeTest` pass.

Hints

- Model the default as its own small resource, not a flag on every address: then "only one default" is automatic.
- Clear it inside `delete`, so it can never point at a deleted address.

#### `challenge/DefaultAddressChallengeTest.java`

``` code
package com.tiffino.addresses;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: PUT /customers/{id}/default-address {"label": "..."}: one default at a time, safe to repeat. */
class DefaultAddressChallengeTest extends ApiTest {

    ResultActions setDefault(String label) throws Exception {
        return mvc.perform(put("/customers/42/default-address").contentType(MediaType.APPLICATION_JSON)
                .content("{\"label\":\"" + label + "\"}"));
    }

    @Test
    void settingTheDefaultTwiceGivesTheSameAnswer() throws Exception {
        putAddress(42, "home", HOME);
        setDefault("home").andExpect(status().isOk()).andExpect(jsonPath("$.label").value("home"));
        setDefault("HOME").andExpect(status().isOk()).andExpect(jsonPath("$.label").value("home"));
        mvc.perform(get("/customers/42/default-address")).andExpect(jsonPath("$.label").value("home"));
    }

    @Test
    void thereIsOnlyOneDefault() throws Exception {
        putAddress(42, "home", HOME);
        putAddress(42, "work", HOME);
        setDefault("home");
        setDefault("work");
        mvc.perform(get("/customers/42/default-address")).andExpect(jsonPath("$.label").value("work"));
    }

    @Test
    void aLabelWithNoAddressIs409() throws Exception {
        setDefault("gym").andExpect(status().isConflict());
    }

    @Test
    void deletingTheDefaultAddressClearsTheDefault() throws Exception {
        putAddress(42, "home", HOME);
        setDefault("home");
        deleteAddress(42, "home");
        mvc.perform(get("/customers/42/default-address")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## "Add a tip" is not idempotent

Product wants `PATCH /orders/{id}` with `{"addTip": 20}`. Why is that PATCH not idempotent, and what happens on a retry? Redesign it two ways: as an idempotent PUT of the total tip, and with an idempotency key (station 085). Which would you choose for a payment-related field, and why?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: a retried POST makes two addresses.
2.  Put the label in the URL, so a request names its address.
3.  Store addresses in a map by label; PUT replaces.
4.  Add Merge Patch, validating the merged result.
5.  Make DELETE return `204` whether or not the address existed; write a replay test per method.

## Design alternatives and trade-offs

| Approach                                       | What it costs                                                                                                          | Verdict            |
|------------------------------------------------|------------------------------------------------------------------------------------------------------------------------|--------------------|
| Client-chosen label in the URL + PUT           | Clients must pick a label; good for a short list like addresses.                                                       | Chosen             |
| POST to a collection for every save            | Each retry adds a copy (the trap).                                                                                     | Wrong              |
| POST to create, PUT/PATCH by server id to edit | Creation still duplicates on retry unless you add an idempotency key (station 085).                                    | With a key         |
| JSON Patch (RFC 6902): a list of operations    | More powerful (move, test, array edits) and more complex; some operations are not idempotent.                          | When needed        |
| DELETE answers 404 when already gone           | Also idempotent; the retry shows an error screen. Station 005 chose this for bookings.                                 | Valid choice       |
| Store `updatedAt` on each save                 | Useful for audit, but then the same PUT twice changes state; keep it out of the compared state or out of the response. | Mind the trade-off |

## Database design

None in this station. With a database, the primary key `(customer_id, label)` enforces "one home", and PUT becomes an upsert: `INSERT … ON CONFLICT (customer_id, label) DO UPDATE`.

# 3 · Go deeper: Production

Reliability  
Idempotent methods let apps, proxies and libraries retry safely. Some HTTP clients and proxies retry idempotent methods automatically but, by default, not POST.

Concurrency  
Idempotent does not mean conflict-free: two phones with different edits still overwrite each other. Challenge 1 adds `ETag`/`If-Match`.

Security  
The customer id in the URL is a demo shortcut; real APIs take it from the login, or anyone can edit anyone's addresses. Addresses are personal data: do not log them.

Maintainability  
The rules for an address live in one record; PUT and PATCH both end in the same validation.

# 3 · Go deeper: Interview

## Interview takeaways

Which HTTP methods are idempotent?

GET, HEAD, OPTIONS, PUT and DELETE are defined as idempotent by RFC 9110. POST is not. PATCH is not guaranteed: it depends on the patch ("set landmark" is, "add 20 to tip" is not).

PUT or PATCH?

PUT replaces the whole resource with the body, so fields left out are removed. PATCH changes only what the patch describes. Use PUT when the client has the full state, PATCH for small changes.

What does null mean in a JSON Merge Patch?

Remove that field. A field left out of the patch is unchanged. That is why Merge Patch cannot set a field to JSON null: null always means remove.

Should a second DELETE return 204 or 404?

Both are idempotent: the server state is the same. 204 makes retries invisible to users; 404 tells the client it was already gone. Pick one, document it, and test it.

Why is POST on /addresses/home a 405 and not a 404?

The URL exists; the method is not supported on it. 405 with an Allow header tells the client which methods do work.

## Self-check rubric

| Area        | Meets the bar                           | Above the bar                                                        |
|-------------|-----------------------------------------|----------------------------------------------------------------------|
| Correctness | All 19 tests pass.                      | You can say which replay test fails if addresses are kept in a list. |
| Design      | Label in the URL; no POST for edits.    | You can explain when POST plus an idempotency key is better.         |
| Tests       | A replay test per method.               | You compared whole states, not just status codes.                    |
| Explanation | PUT against PATCH in one sentence each. | You can explain why idempotent is not the same as conflict-free.     |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any write endpoint you review:

- If this request arrives twice, what changes the second time?
- Is POST used for something that should be PUT?
- Does a repeat DELETE give an answer the client can live with?
- Does the stored state include anything that changes on every save (time, counters)?
