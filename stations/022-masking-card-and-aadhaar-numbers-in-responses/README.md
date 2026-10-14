# Station 022 · Masking card and Aadhaar numbers in responses

Foundations · 0–1 years · Core · Fintech · Types: Security

Spring Boot 4.1.1 · Java 25 · Spring MVC · Spring Security 7 · Jackson 3 ValueSerializer · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Two demo customers in memory. Every number is made up; the card numbers are the well-known test numbers. Sign-in is HTTP Basic with demo passwords.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 15 tests.

# 1 · Understand

## The problem in real life

1.  **Asha shares a screenshot with support**

    The app shows XXXX XXXX 0123 for her Aadhaar. But the network log in the same bug report shows the full 12 digits: the API sent them; only the screen hid them.

2.  **The logs agree**

    Every profile request logged by the gateway, and every crash report with the response attached, holds full card and Aadhaar numbers.

3.  **The fix**

    Mask on the server, on the type itself: any field holding one of these values is masked in every response and every log line, with no switch to turn it off.

If the screen hides it but the response carries it, it is not hidden.

## What are we building?

`GET /customers/{id}/profile` returns a customer's profile with every sensitive number masked, to the customer, and to support, with no exceptions.

## An everyday analogy

A bank posts your new debit card in an envelope with a window that shows only your name. Holding the envelope up to the light must not reveal the card number either: the protection is in the envelope, not in how carefully people hold it.

## How it works in 4 steps

1.  **Sign in**: unknown callers get `401`, roles that may not read profiles `403`.
2.  **Check ownership**: a customer sees only their own profile; anything else is the same `404` as a missing one.
3.  **Load the profile**: sensitive values are held in a `Sensitive` type, never a plain string.
4.  **Write JSON**: the type's serializer writes the masked form. There is no other form to write.

Check yourself: support needs to confirm a caller's Aadhaar. Should support get the full number?

No. Support can ask for the last four and compare, or (challenge 2) ask the server whether they match. Every person who can see a full number is another place it can leak from.

## What this station is not

- **Not encryption at rest.** The numbers sit in memory in full; storing them safely is a separate concern.
- **Not real sign-in.** HTTP Basic with demo users.
- **Not legal advice.** Card and Aadhaar rules are summarised; check the current versions.

## Key terms

| Term             | Simple meaning                                                                 | Everyday example                                          | In this project                           |
|------------------|--------------------------------------------------------------------------------|-----------------------------------------------------------|-------------------------------------------|
| **Masking**      | Showing only part of a number, enough to recognise it, never enough to use it. | A receipt that prints XXXX XXXX XXXX 1111.                | `Sensitive.masked()`                      |
| **API response** | What the server actually sends. Logs, proxies and screenshots keep it.         | The parcel, not the label stuck on top.                   | The JSON body                             |
| **Serializer**   | The code that turns a Java object into JSON.                                   | A translator who always leaves certain words out.         | `MaskingSerializer`                       |
| **toString**     | What Java prints when an object is logged.                                     | What gets read aloud when someone says "what is in this?" | `Sensitive.toString()`                    |
| **401 / 403**    | 401: we do not know who you are. 403: we know, and you may not.                | No ticket; a ticket for another show.                     | Wrong password; marketing role            |
| **Enumeration**  | Learning which ids exist by watching which answers differ.                     | Trying door handles to see which flats are occupied.      | Another customer's profile is a plain 404 |

# 2 · Build: Spec

## Business problem

**Tijori** (a fictional fintech app) masks card and Aadhaar numbers in its app's screens, but its profile API returns them in full. They appear in gateway logs, crash reports and the network tab of every bug report. Support tooling has a "show full" switch nobody remembers adding.

## Acceptance criteria

1.  **Given** a customer reading their own profile, **then** Aadhaar shows as `XXXX XXXX 0123`, cards as `XXXX XXXX XXXX 1111`, account and mobile with only the last 4, email as `a***@example.com`.
2.  **Given** any response, **then** no full number from the data appears anywhere in it, and no run of five digits.
3.  **Given** support, **then** any profile, masked exactly the same; `?full=true` or any other parameter changes nothing.
4.  **Given** one customer asking for another's profile, **then** the same `404` as for an id that does not exist.
5.  **Given** no or wrong credentials, **then** `401`; a marketing user, `403`.
6.  **Given** a profile written to a log, **then** it is masked there too.

## Requirements

- Sensitive values have their own type; its serializer and `toString` both mask.
- Values shorter than 8 characters show no digits at all.
- Error responses never repeat the requested id in their detail.
- No CVV is stored: card rules forbid keeping it after authorisation.

## Learning objectives

- Write a Jackson 3 `ValueSerializer` and attach it to a type.
- Mask per field with rules that match each kind of number.
- Prove masking with tests that search the whole response, for every role.
- Answer 401, 403 and "not yours" without leaking which ids exist.

# 2 · Build: API contract

## Endpoint

| Method | Path                      | Purpose                                                  |
|--------|---------------------------|----------------------------------------------------------|
| `GET`  | `/customers/{id}/profile` | The profile, masked. Customers: their own; support: any. |

## Demo users

| User  | Password        | Role      | Profiles    |
|-------|-----------------|-----------|-------------|
| asha  | asha-demo-pass  | CUSTOMER  | c-1001 only |
| ravi  | ravi-demo-pass  | CUSTOMER  | c-1002 only |
| neha  | neha-demo-pass  | SUPPORT   | Any, masked |
| kiran | kiran-demo-pass | MARKETING | None (403)  |

## Masking rules

| Field                   | Shown as                                         |
|-------------------------|--------------------------------------------------|
| `aadhaar`               | `XXXX XXXX 0123`                                 |
| `cards[].number`        | `XXXX XXXX XXXX 1111` (network and expiry shown) |
| `bankAccount`, `mobile` | X for every digit but the last 4                 |
| `email`                 | First letter, `***`, the domain                  |

## Status codes

| Status | When                                            |
|--------|-------------------------------------------------|
| 200    | Your profile, or any profile for support        |
| 401    | No credentials or a wrong password              |
| 403    | A role that may not read profiles               |
| 404    | No such profile, or not yours (the same answer) |

## Captured examples

Captured with curl from the running app on 14 Oct 2026. `-u` is shown as the `Authorization` header curl sends. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: Asha reads her own profile

**Why:** every number masked by its own rule; name, network and expiry shown.

Request

``` code
GET /customers/c-1001/profile HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 200 
X-Content-Type-Options: nosniff
X-XSS-Protection: 0
Cache-Control: no-cache, no-store, max-age=0, must-revalidate
Pragma: no-cache
Expires: 0
X-Frame-Options: DENY
Content-Type: application/json
Content-Length: 225

{
  "customerId": "c-1001",
  "name": "Asha Rao",
  "mobile": "XXXXXX3210",
  "email": "a***@example.com",
  "aadhaar": "XXXX XXXX 0123",
  "cards": [
    {
      "network": "VISA",
      "number": "XXXX XXXX XXXX 1111",
      "expiry": "08/29"
    }
  ],
  "bankAccount": "XXXXXXXXXX5678"
}
```

### Case 2: support reads Ravi's profile

**Why:** support may read any profile, and sees exactly what the customer sees.

Request

``` code
GET /customers/c-1002/profile HTTP/1.1
Authorization: Basic bmVoYTpuZWhhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 200 
X-Content-Type-Options: nosniff
X-XSS-Protection: 0
Cache-Control: no-cache, no-store, max-age=0, must-revalidate
Pragma: no-cache
Expires: 0
X-Frame-Options: DENY
Content-Type: application/json
Content-Length: 300

{
  "customerId": "c-1002",
  "name": "Ravi Kumar",
  "mobile": "XXXXXX6780",
  "email": "r***@example.com",
  "aadhaar": "XXXX XXXX 1234",
  "cards": [
    {
      "network": "MASTERCARD",
      "number": "XXXX XXXX XXXX 4444",
      "expiry": "01/28"
    },
    {
      "network": "VISA",
      "number": "XXXX XXXX XXXX 1881",
      "expiry": "11/27"
    }
  ],
  "bankAccount": "XXXXXXXXXX3344"
}
```

### Case 3: support adds ?full=true

**Why:** there is no unmasked form to switch to. The parameter is ignored.

Request

``` code
GET /customers/c-1001/profile?full=true HTTP/1.1
Authorization: Basic bmVoYTpuZWhhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 200 
X-Content-Type-Options: nosniff
X-XSS-Protection: 0
Cache-Control: no-cache, no-store, max-age=0, must-revalidate
Pragma: no-cache
Expires: 0
X-Frame-Options: DENY
Content-Type: application/json
Content-Length: 225

{
  "customerId": "c-1001",
  "name": "Asha Rao",
  "mobile": "XXXXXX3210",
  "email": "a***@example.com",
  "aadhaar": "XXXX XXXX 0123",
  "cards": [
    {
      "network": "VISA",
      "number": "XXXX XXXX XXXX 1111",
      "expiry": "08/29"
    }
  ],
  "bankAccount": "XXXXXXXXXX5678"
}
```

### Case 4: Asha asks for Ravi's profile

**Why:** the same 404 as a missing id, so nobody can find out which ids exist.

Request

``` code
GET /customers/c-1002/profile HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 404 
X-Content-Type-Options: nosniff
X-XSS-Protection: 0
Cache-Control: no-cache, no-store, max-age=0, must-revalidate
Pragma: no-cache
Expires: 0
X-Frame-Options: DENY
Content-Type: application/problem+json

{
  "detail": "No customer profile here for you.",
  "instance": "/customers/c-1002/profile",
  "status": 404,
  "title": "Profile not found"
}
```

### Case 5: no credentials

**Why:** `401` with a `WWW-Authenticate` header.

Request

``` code
GET /customers/c-1001/profile HTTP/1.1
```

Response

``` code
HTTP/1.1 401 
WWW-Authenticate: Basic realm="tijori"
X-Content-Type-Options: nosniff
X-XSS-Protection: 0
Cache-Control: no-cache, no-store, max-age=0, must-revalidate
Pragma: no-cache
Expires: 0
X-Frame-Options: DENY
Content-Type: application/problem+json
Content-Length: 131

{
  "title": "Sign-in required",
  "status": 401,
  "detail": "Send valid credentials to use this API.",
  "instance": "/customers/c-1001/profile"
}
```

### Case 6: a marketing user

**Why:** signed in, but the role may not read profiles: `403`.

Request

``` code
GET /customers/c-1001/profile HTTP/1.1
Authorization: Basic a2lyYW46a2lyYW4tZGVtby1wYXNz
```

Response

``` code
HTTP/1.1 403 
X-Content-Type-Options: nosniff
X-XSS-Protection: 0
Cache-Control: no-cache, no-store, max-age=0, must-revalidate
Pragma: no-cache
Expires: 0
X-Frame-Options: DENY
Content-Type: application/problem+json
Content-Length: 130

{
  "title": "Not allowed",
  "status": 403,
  "detail": "Your account cannot read customer profiles.",
  "instance": "/customers/c-1001/profile"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                    | What happens                     | Proved by                                                         |
|-----------------------------------------|----------------------------------|-------------------------------------------------------------------|
| Own profile                             | Every field masked by its rule   | `aCustomerSeesTheirOwnProfileMaskedFieldByField`                  |
| Unknown id (support)                    | `404`                            | `aProfileThatDoesNotExistIs404`                                   |
| No credentials; wrong password          | `401`                            | `noCredentialsOrAWrongPasswordIs401`                              |
| Marketing user                          | `403`                            | `marketingCannotReadProfilesAtAll`                                |
| Asha asks for Ravi's profile            | `404`, identical to a missing id | `aCustomerCannotReadAnotherCustomersProfileAndCannotTellItExists` |
| Support, both profiles                  | Masked, no full number           | `supportSeesAnyProfileButStillMasked`                             |
| ?full, ?unmasked, ?raw, ?debug, X-Debug | Still masked                     | `noParameterOrHeaderUnmasks`                                      |
| Script and SQL-looking ids              | `404` with a fixed detail        | `maliciousIdsAreNotFoundAndTheDetailNeverEchoesThem`              |
| Encoded slashes, a null byte            | `400` from the firewall          | `pathTricksAreStoppedByTheFirewallBeforeAnyController`            |
| Short or odd values                     | No digits shown                  | `tooShortOrOddValuesShowNothing`                                  |
| A card in a log line                    | Masked                           | `toStringIsMaskedSoLogsAreToo`                                    |

## The trap

Plausible but wrong

Masking in the UI only; the full number is still in the API response.

The first test serialises the old profile, plain strings, and finds the full Aadhaar and card numbers in the JSON and in its `toString`. The second searches the real response for every full number in the data, and for any run of five digits: none. The third shows a plain `JsonMapper`, not Spring's, masking too, because the rule is on the type.

``` code
package com.tijori.profiles;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The first test written for this station: it reproduces the bug before the fix. */
class FullNumberTrapTest extends ApiTest {

    /** The "before" profile: plain strings. The app masked them on screen; the API sent them whole. Kept only in tests. */
    record OldProfile(String name, String aadhaar, String cardNumber) {
    }

    @Test
    void theOldResponseCarriesTheFullNumbersWhateverTheScreenShows() {
        String json = JsonMapper.builder().build().writeValueAsString(new OldProfile("Asha Rao", "234567890123", "4111111111111111"));
        assertThat(json).contains("234567890123").contains("4111111111111111");   // in every log, proxy and screenshot of the response
        assertThat(new OldProfile("Asha Rao", "234567890123", "4111111111111111").toString()).contains("234567890123");
    }

    @Test
    void theRealResponseIsMaskedBeforeItLeavesTheServer() throws Exception {
        String body = profileAs("asha", "c-1001")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.aadhaar").value("XXXX XXXX 0123"))
                .andExpect(jsonPath("$.cards[0].number").value("XXXX XXXX XXXX 1111"))
                .andReturn().getResponse().getContentAsString();
        RAW_NUMBERS.forEach(raw -> assertThat(body).doesNotContain(raw));
        assertThat(body).doesNotContainPattern("\\d{5,}");   // no run of five digits anywhere in the profile
    }

    @Test
    void anyMapperMasksBecauseTheRuleIsOnTheType() {
        // Not just Spring's configured mapper: a plain one, as someone might use for logging, masks too.
        String json = JsonMapper.builder().build().writeValueAsString(Sensitive.aadhaar("234567890123"));
        assertThat(json).isEqualTo("\"XXXX XXXX 0123\"");
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
./mvnw test                 # all 15 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

``` code
# Your own profile, masked
curl -u asha:asha-demo-pass http://localhost:8080/customers/c-1001/profile

# Someone else's: 404
curl -i -u asha:asha-demo-pass http://localhost:8080/customers/c-1002/profile
```

## Troubleshooting

| You see                                 | Cause                        | Fix                                                      |
|-----------------------------------------|------------------------------|----------------------------------------------------------|
| `401`                                   | Wrong user or password.      | Use a demo user from the API contract.                   |
| `404` for an id you can see in the data | It is not your profile.      | Sign in as its owner, or as support.                     |
| `release version 25 not supported`      | Maven is using an older JDK. | Point `JAVA_HOME` at JDK 25, or add `-Djava.version=21`. |

## Project layout

``` tree
stations/022-masking-card-and-aadhaar-numbers-in-responses/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tijori/profiles/
│   ├── SecurityConfig.java   ├── ProfileController.java   ├── Sensitive.java
│   ├── Customers.java        ├── ProblemResponses.java    └── ProfilesApplication.java
├── src/test/java/com/tijori/profiles/   (see Tests)
├── review/                   The flawed version for the Review tab
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/tijori/profiles/SecurityConfig.java`

Does  
HTTP Basic, four demo users, and which roles may read profiles.

Why  
Role checks at the door; ownership checks in the controller, where the id is known.

Without it  
Every signed-in user reads every profile.

#### `src/main/java/com/tijori/profiles/ProfileController.java`

Does  
Checks ownership and returns the profile.

Why  
Someone else's profile is the same 404 as a missing one; there is no "full" switch.

Without it  
`?full=true` for support; a 403 that confirms the id exists.

#### `src/main/java/com/tijori/profiles/Sensitive.java`

Does  
The type for numbers that must never leave in full, with its masking rules and serializer.

Why  
`@JsonSerialize` on the type: every field, every mapper, every log line masks.

Without it  
The trap: plain strings, masked only on screen.

- One `switch` over `Kind` holds every rule.
- `toString()` is overridden, because logs print it.
- Under 8 characters, no digits are shown at all.

#### `src/main/java/com/tijori/profiles/Customers.java`

Two made-up customers, and which demo user is which customer. No CVV anywhere.

#### `src/main/java/com/tijori/profiles/ProblemResponses.java`

401 and 403 written as problem JSON, since they happen before any controller.

#### `src/main/resources/application.yaml`

Problem bodies for every error.

#### `src/main/java/com/tijori/profiles/ProfilesApplication.java`

Standard Spring Boot entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                | Test class                | Result |
|---------------|------------------------------------------------------------|---------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                   | `ProfileContractTest` (2) | pass   |
| Every station | Reproduce the failure before the fix                       | `FullNumberTrapTest` (3)  | pass   |
| Security      | 401, 403, one user reading another's data, malicious input | `ProfileSecurityTest` (7) | pass   |
| This station  | Each masking rule and toString                             | `MaskingTest` (3)         | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.profiles.ProfileContractTest
[INFO] Tests run: 7, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.profiles.ProfileSecurityTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.profiles.MaskingTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.profiles.FullNumberTrapTest
[INFO] Tests run: 15, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/tijori/profiles/FullNumberTrapTest.java`

Written first: the old profile's full numbers, the real response searched for them, and a plain mapper masking.

#### `src/test/java/com/tijori/profiles/ProfileSecurityTest.java`

401, 403, someone else's profile, support, unmask attempts, malicious ids and the firewall.

#### `src/test/java/com/tijori/profiles/ProfileContractTest.java`

The masked profile field by field, and a missing profile.

#### `src/test/java/com/tijori/profiles/MaskingTest.java`

Each rule, odd values, and `toString`.

#### `src/test/java/com/tijori/profiles/ApiTest.java`

Shared setup: MockMvc, sign-in as a demo user, and every full number in the data.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/tijori/profiles/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=PanChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 15 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 18 tests pass (15 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 15 minutes

## Add a PAN

Profiles gain a PAN (made up: ABCDE1234F for Asha). Show it as `XXXXXX234F`.

**Done when:** the test in `PanChallengeTest` passes, and no response contains the full PAN.

Hints

- One more `Kind`, one more `case`: the serializer and `toString` follow on their own.
- Add the field to `Profile` as `Sensitive`, never as a `String`.

#### `challenge/PanChallengeTest.java`

``` code
package com.tijori.profiles;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/** Challenge 1: profiles gain a PAN (ABCDE1234F for Asha, made up), shown as XXXXXX234F. */
class PanChallengeTest extends ApiTest {

    @Test
    void thePanIsMaskedLikeEveryOtherNumber() throws Exception {
        String body = profileAs("asha", "c-1001")
                .andExpect(jsonPath("$.pan").value("XXXXXX234F"))
                .andReturn().getResponse().getContentAsString();
        assertThat(body).doesNotContain("ABCDE1234F");
        assertThat(Sensitive.pan("ABCDE1234F").toString()).isEqualTo("XXXXXX234F");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Verify without revealing

Add `POST /customers/{id}/aadhaar-checks` with `{"last4": "0123"}`, for support only. It answers `{"match": true|false}` and never shows the number. Only exactly 4 digits are accepted.

**Done when:** both tests in `VerifyWithoutRevealingChallengeTest` pass.

Hints

- Compare inside `Sensitive`, so the raw value never leaves the type.
- `MessageDigest.isEqual` compares in the same time whether it matches or not.
- Restrict the path to SUPPORT in `SecurityConfig`.

#### `challenge/VerifyWithoutRevealingChallengeTest.java`

``` code
package com.tijori.profiles;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: POST /customers/{id}/aadhaar-checks with {"last4": "0123"} lets support check what a caller reads out,
 * without the API ever showing the number. Only support may call it.
 */
class VerifyWithoutRevealingChallengeTest extends ApiTest {

    ResultActions check(String user, String id, String last4) throws Exception {
        return mvc.perform(post("/customers/{id}/aadhaar-checks", id).with(httpBasic(user, user + "-demo-pass"))
                .contentType(MediaType.APPLICATION_JSON).content("{\"last4\":\"" + last4 + "\"}"));
    }

    @Test
    void supportLearnsOnlyWhetherItMatches() throws Exception {
        check("neha", "c-1001", "0123").andExpect(status().isOk()).andExpect(jsonPath("$.match").value(true));
        check("neha", "c-1001", "9999").andExpect(status().isOk()).andExpect(jsonPath("$.match").value(false));
        check("neha", "c-9999", "0123").andExpect(status().isNotFound());
    }

    @Test
    void onlySupportMayCheckAndOnlyFourDigitsAreAccepted() throws Exception {
        check("asha", "c-1001", "0123").andExpect(status().isForbidden());
        check("neha", "c-1001", "123").andExpect(status().isBadRequest());
        check("neha", "c-1001", "234567890123").andExpect(status().isBadRequest());   // no guessing the whole number
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Who may ever see a full number?

The bank's card team says a dispute process needs the full card number once a year. Design it: who asks, who approves, what is logged, where the number is shown, and for how long. Would you build it into this API at all?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the old profile's JSON and `toString` both carry the full numbers.
2.  Introduce `Sensitive` with its rules, serializer and `toString`; test each rule.
3.  Change every sensitive field to `Sensitive`; search the whole response in tests, for every role.
4.  Add sign-in, roles and the ownership check, with answers that do not reveal which ids exist.

## Design alternatives and trade-offs

| Approach                                    | What it costs                                             | Verdict      |
|---------------------------------------------|-----------------------------------------------------------|--------------|
| A type with its own serializer and toString | Wrapping values in a type.                                | Chosen       |
| Masking in the UI                           | The response still carries everything.                    | The trap     |
| `@JsonSerialize` on each field              | Works until someone adds a field and forgets.             | Fragile      |
| A response DTO that copies masked strings   | Safe for responses; logs of the domain object still leak. | Half the job |
| A filter that regex-masks every response    | Guesses what is a number; misses some, breaks others.     | Avoid        |

## Database design

None in this station. With a database: card numbers are not stored at all (a token from the card network instead), and Aadhaar numbers only where the law allows, encrypted, in a separate store. The profile table keeps the last 4 digits for display.

# 3 · Go deeper: Production

Cards  
PCI DSS, the card industry's security standard, limits what may be displayed (at most the first few and the last four digits) and forbids keeping the CVV after authorisation. Most apps should never see a card number at all: card networks issue tokens.

Aadhaar  
UIDAI's masked Aadhaar shows only the last four digits. Organisations that keep Aadhaar numbers face strict storage rules; check UIDAI's current regulations before storing any.

Logs  
A masked `toString` protects the common case. Request and response body logging must still be off for these endpoints.

Tests  
Search the whole response for every raw value, for every role. A test that checks one field misses the next one someone adds.

# 3 · Go deeper: Interview

## Interview takeaways

Why is masking in the UI not enough?

The UI is one reader of the response. Logs, proxies, browser network tabs, crash reports and other clients all see the raw response.

Where would you put masking in Spring?

On the type: a value class whose JSON serializer writes the masked form and whose toString masks too. Then every field of that type is masked everywhere, by default.

How do you write a Jackson 3 serializer?

Extend tools.jackson.databind.ValueSerializer\<T\> and override serialize(value, JsonGenerator, SerializationContext). Attach it with @JsonSerialize(using = ...) or a module.

401 or 403 or 404 for someone else's data?

401 if we do not know who you are, 403 if your role may not do this at all, and 404 for a specific item that is not yours, so the response does not confirm it exists.

How do you test that masking holds?

Search the whole body for every raw value in the test data, for each role and parameter, and check toString as well.

## Self-check rubric

| Area        | Meets the bar                               | Above the bar                                                   |
|-------------|---------------------------------------------|-----------------------------------------------------------------|
| Correctness | All 15 tests pass.                          | You found all four flaws in the Review tab before opening them. |
| Masking     | Every sensitive field masked by type.       | You can say why toString matters.                               |
| Access      | 401, 403 and not-yours behave as specified. | You can explain enumeration.                                    |
| Explanation | Why server-side masking.                    | Who, if anyone, should see a full number.                       |

# 3 · Go deeper: Review

## The pull request

A teammate made support's life easier: the Aadhaar mask "keeps the useful digits", `toString` is "readable again", support can ask for full numbers during KYC calls, and a "redundant" ownership check is gone. The happy-path tests pass. Read both files and list every problem before opening the findings.

#### `review/Sensitive.java`

``` code
package com.tijori.profiles;

import tools.jackson.core.JsonGenerator;
import tools.jackson.databind.SerializationContext;
import tools.jackson.databind.ValueSerializer;
import tools.jackson.databind.annotation.JsonSerialize;

import java.util.Objects;

/**
 * A value that must never leave the server in full: an Aadhaar, card, account or mobile number, or an email.
 * The masking lives on the type, not on each field or page: the JSON serializer and toString() both mask, so a
 * new field of this type is masked in responses and in logs without anyone remembering to.
 */
@JsonSerialize(using = Sensitive.MaskingSerializer.class)
record Sensitive(Kind kind, String raw) {

    enum Kind {
        /** "XXXX XXXX 0123": the last 4 digits, as on a masked Aadhaar. */
        AADHAAR,
        /** "XXXX XXXX XXXX 1111": the last 4 digits only. */
        CARD,
        /** "XXXXXXXXXX5678": the last 4 digits, same length. */
        ACCOUNT,
        /** "XXXXXX3210". */
        MOBILE,
        /** "a***@example.com": the first letter and the domain. */
        EMAIL
    }

    Sensitive {
        Objects.requireNonNull(kind);
        Objects.requireNonNull(raw);
    }

    static Sensitive aadhaar(String digits) {
        return new Sensitive(Kind.AADHAAR, digits);
    }

    static Sensitive card(String digits) {
        return new Sensitive(Kind.CARD, digits);
    }

    static Sensitive account(String digits) {
        return new Sensitive(Kind.ACCOUNT, digits);
    }

    static Sensitive mobile(String digits) {
        return new Sensitive(Kind.MOBILE, digits);
    }

    static Sensitive email(String address) {
        return new Sensitive(Kind.EMAIL, address);
    }

    String masked() {
        return switch (kind) {
            case AADHAAR -> "XXXX XXXX " + raw.substring(0, 4);   // "keep 4 digits so support can match it"
            case CARD -> "XXXX XXXX XXXX " + last4();
            case ACCOUNT, MOBILE -> "X".repeat(Math.max(0, raw.length() - 4)) + last4();
            case EMAIL -> {
                int at = raw.indexOf('@');
                yield at < 1 ? "***" : raw.charAt(0) + "***" + raw.substring(at);
            }
        };
    }

    /** Fewer than 8 characters is too short to show any of it safely. */
    private String last4() {
        return raw.length() < 8 ? "XXXX" : raw.substring(raw.length() - 4);
    }

    // toString() removed: "the masked one made debugging impossible".

    static final class MaskingSerializer extends ValueSerializer<Sensitive> {
        @Override
        public void serialize(Sensitive value, JsonGenerator gen, SerializationContext ctxt) {
            gen.writeString(value.masked());
        }
    }
}
```

#### `review/ProfileController.java`

``` code
package com.tijori.profiles;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.security.core.Authentication;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
class ProfileController {

    private final Customers customers;

    ProfileController(Customers customers) {
        this.customers = customers;
    }

    /** Support can pass ?full=true to read the numbers out to a customer during KYC verification. */
    @GetMapping("/customers/{id}/profile")
    Object profile(@PathVariable String id, @RequestParam(defaultValue = "false") boolean full, Authentication who) {
        boolean support = who.getAuthorities().stream().anyMatch(a -> a.getAuthority().equals("ROLE_SUPPORT"));
        // The app only ever shows a customer their own id, so no ownership check is needed here.
        Customers.Profile p = customers.profile(id).orElseThrow(ProfileController::notFound);
        if (support && full) {
            return Map.of("customerId", p.customerId(), "name", p.name(), "aadhaar", p.aadhaar().raw(),
                    "cards", p.cards().stream().map(c -> c.number().raw()).toList());
        }
        return p;
    }

    /** The id is not echoed: it is whatever the caller typed, scripts included. */
    private static ErrorResponseException notFound() {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No customer profile here for you.");
        p.setTitle("Profile not found");
        return new ErrorResponseException(HttpStatus.NOT_FOUND, p, null);
    }
}
```

## Findings

1The Aadhaar mask keeps the first four digits

"Support can match it" sounds helpful, but the masked Aadhaar standard shows the last four; the first four plus the last four that other systems show is two-thirds of the number.

**Test evidence:** `aCustomerSeesTheirOwnProfileMaskedFieldByField`: got `XXXX XXXX 3456`; also `eachKindShowsOnlyWhatItMay` and `theRealResponseIsMaskedBeforeItLeavesTheServer`.

2`toString()` removed "for debugging"

The record's default `toString` prints the raw value, so every log line with a profile or card now holds the full number.

**Test evidence:** `toStringIsMaskedSoLogsAreToo`, and `anyMapperMasksBecauseTheRuleIsOnTheType` fails with it.

3Support gets `?full=true`

A convenience for KYC calls that turns a support login into a full-number export, and puts those numbers into every log of that request.

**Test evidence:** `noParameterOrHeaderUnmasks`: `[full]` returned the raw Aadhaar.

4The ownership check is gone

"The app only shows your own id": but anyone can call the API with any id. Asha reads Ravi's profile.

**Test evidence:** `aCustomerCannotReadAnotherCustomersProfileAndCannotTellItExists`: got 200.

## Same tests, flawed version

From `docs/review-run.txt`: the two flawed files copied over the real ones, then the full suite run.

| Test class            | Fixed version | Flawed version |
|-----------------------|---------------|----------------|
| `FullNumberTrapTest`  | 3 / 3         | 1 / 3          |
| `MaskingTest`         | 3 / 3         | 1 / 3          |
| `ProfileContractTest` | 2 / 2         | 1 / 2          |
| `ProfileSecurityTest` | 7 / 7         | 5 / 7          |

Each change was made for a person: support, a developer debugging, a product shortcut. The tests catch them because they ask what a log, an attacker or another customer would see.
