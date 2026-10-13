# Station 006 · One error shape for a banking API

Foundations · 0–1 years · Core · Fintech · Types: Security

Spring Boot 4.1.1 · Java 25 · Spring MVC · Spring Security 7 · ProblemDetail (RFC 9457) · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The IFSC directory is a fixed list of four branches inside the app, and beneficiaries live in memory. No bank is called and no money moves. Sign-in is HTTP Basic with three demo users.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 20 tests.

# 1 · Understand

## The problem in real life

1.  **Asha adds Ravi as a beneficiary**

    She types Ravi's account number and IFSC into the Tijori app and taps Save.

2.  **Something fails, but what?**

    One endpoint returns `{"error":"…"}`, another an HTML page, another a Java stack trace that names the database server. The app cannot tell "wrong IFSC" (Asha should fix it) from "server down" (try later).

3.  **The fix**

    Every error leaves the API in one shape, with a status code and a type that say what to do next, and without any internal detail an attacker could use.

An error message has two readers: the app, which must decide what to do, and anyone probing the API, who looks for clues. Write for the first and give nothing to the second.

## What are we building?

A small beneficiary API (add one, read one) where every failure, from bad input to a sign-in problem to a bug, comes back as an RFC 9457 problem with its own `type`. Unexpected errors return only an `errorId`; the details go to the log.

## An everyday analogy

A bank branch with one complaints desk. Whatever goes wrong, you get the same printed form: a category ("wrong IFSC", "system down, come back in an hour"), a short explanation, and a reference number. The clerk does not hand you the internal incident report with server names and staff notes; that stays in the back office, filed under your reference number.

## How it works in 4 steps

1.  **Code throws a business exception** that says what happened: `UnknownIfsc`, `DuplicateBeneficiary`, `IfscDirectoryUnavailable`.
2.  **One advice class catches them all** and picks a status and a problem type for each.
3.  **Anything unexpected** becomes a `500` with a random `errorId`; the full exception is logged under that id.
4.  **Sign-in errors** (401, 403) happen before any controller, so the security layer writes the same shape itself.

Check yourself: Ravi asks for a beneficiary id that belongs to Asha. Why does he get 404 and not 403?

403 would tell Ravi "this id exists, it is just not yours", which confirms that the id is real. 404 gives him exactly the same answer as for an id that does not exist, so he learns nothing about other customers.

## What this station is not

- **A simulation.** The IFSC directory is four branches in a list; nothing calls a bank. No money moves.
- **Demo sign-in.** HTTP Basic with three in-memory users (passwords stored as bcrypt hashes). Real banking apps use stronger sign-in, covered in later stations.
- **No database.** Beneficiaries are lost on restart.

## Key terms

| Term                           | Simple meaning                                                                                       | Everyday example                                                  | In this project                                 |
|--------------------------------|------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|-------------------------------------------------|
| **Beneficiary**                | A person or account you have saved so you can send money to them later.                              | A saved contact in your phone.                                    | Ravi's HDFC account, saved by Asha.             |
| **IFSC**                       | An 11-character code that identifies one bank branch in India.                                       | A PIN code, but for a bank branch.                                | `HDFC0001234`                                   |
| **Exception**                  | Java's way to stop normal work and report that something went wrong.                                 | Pulling the emergency chain on a train.                           | `UnknownIfsc`, `BeneficiaryNotFound`            |
| **`@RestControllerAdvice`**    | One class that turns exceptions from every controller into HTTP responses.                           | A single complaints desk for the whole bank.                      | `ApiErrors`                                     |
| **Problem details (RFC 9457)** | A standard JSON shape for errors: `type`, `title`, `status`, `detail`, `instance`.                   | One standard complaint form, whatever went wrong.                 | Every error in this API.                        |
| **Problem type**               | A fixed URI naming the kind of error, so code can branch on it.                                      | A form's category box: "lost card" or "wrong charge".             | `…/problems/unknown-ifsc`                       |
| **Stack trace**                | The list of methods that were running when an exception happened, with class names and line numbers. | A map of the building with every room labelled.                   | Goes to the log only, never to a client.        |
| **401 / 403**                  | 401: we do not know who you are. 403: we know, and you may not do this.                              | No ID card at the gate / an ID card without access to this floor. | No credentials / a viewer adding a beneficiary. |

# 2 · Build: Spec

## Business problem

**Tijori** (a fictional digital bank) has a beneficiary API that grew one endpoint at a time. Each one fails differently: a string, a map, Spring's default HTML page, or the exception message with a stack trace. The app team cannot tell "wrong IFSC" (ask the customer to check) from "IFSC service down" (ask them to retry), so every failure shows "Something went wrong". A security review found that one error response named the internal database host and the SQL being run.

## Acceptance criteria

1.  **Given** any error from any endpoint, **then** the body is `application/problem+json` with `type`, `title`, `status`, `detail` and `instance`, and never an exception name or stack trace.
2.  **Given** invalid fields, **then** `400` type `invalid-request` with one message per field; no message repeats what was sent.
3.  **Given** a well-formed IFSC that no branch has, **then** `400` type `unknown-ifsc`. **Given** the IFSC directory is down, **then** `503` type `ifsc-directory-unavailable` with `Retry-After`.
4.  **Given** the same account and IFSC twice, **then** `409` naming the existing beneficiary.
5.  **Given** an unexpected failure, **then** `500` type `internal-error` with an `errorId`, and the log holds the exception under that id.
6.  **Given** no or wrong credentials, **then** `401` (same body for both). **Given** a viewer adding, **then** `403`. **Given** another customer's id, **then** `404`, identical to an unknown id.

## Requirements

- One `@RestControllerAdvice` maps every exception. Controllers have no `try`/`catch`.
- Each kind of error has a stable type URI under `https://tijori.example/problems/`.
- Error text states the rule, never the input: no reflected scripts, SQL or IDs from the request.
- The owner of a beneficiary is the signed-in customer, never a body field.
- Responses show only the last 4 digits of an account number.

## Learning objectives

- Write business exceptions and map them in one `@RestControllerAdvice`.
- Build RFC 9457 `ProblemDetail` responses with types an app can branch on.
- Choose 400, 404, 409 or 503 by what the client should do next.
- Log the details, return only an id: never leak stack traces or messages.
- Give 401 and 403 from Spring Security the same shape.

# 2 · Build: API contract

## Endpoints

| Method | Path                  | Who                                            | Purpose              |
|--------|-----------------------|------------------------------------------------|----------------------|
| `POST` | `/beneficiaries`      | Customers (asha, ravi)                         | Add a beneficiary    |
| `GET`  | `/beneficiaries/{id}` | Any signed-in user; only the owner's are found | Read one beneficiary |

## Request body

| Field           | Rule                                                                                              |
|-----------------|---------------------------------------------------------------------------------------------------|
| `name`          | 2–100 letters, spaces, dots, apostrophes or hyphens.                                              |
| `accountNumber` | 9 to 18 digits. Responses show only the last 4.                                                   |
| `ifsc`          | 11 characters: 4 letters, `0`, 6 letters or digits. Lower case is accepted and stored upper case. |

## Error catalogue

Every error has the same fields. The `type` tells the app what to do.

| Status | Type (after `…/problems/`)   | When                                                                      | What the app should do                             |
|--------|------------------------------|---------------------------------------------------------------------------|----------------------------------------------------|
| 400    | `invalid-request`            | Fields break a rule (with `errors`), or a path value has the wrong format | Show the messages; let the customer fix the fields |
| 400    | `unknown-ifsc`               | Well-formed IFSC that no branch has                                       | Ask the customer to check the IFSC                 |
| 401    | `unauthenticated`            | No or wrong credentials                                                   | Sign in again                                      |
| 403    | `forbidden`                  | Signed in, but this account cannot do this                                | Hide the action for this user                      |
| 404    | `beneficiary-not-found`      | No such id on your account (including another customer's)                 | Refresh the list                                   |
| 409    | `duplicate-beneficiary`      | This account is already saved; `existingBeneficiaryId` names it           | Open the existing one                              |
| 500    | `internal-error`             | A bug or unexpected failure; only `errorId` is given                      | Apologise; show the errorId for support            |
| 503    | `ifsc-directory-unavailable` | The IFSC check could not run; nothing was saved                           | Retry after `Retry-After` seconds                  |

Errors Spring raises itself (broken JSON, an unknown path, a wrong method) use the same fields with `type: about:blank`, which RFC 9457 defines as "the HTTP status says it all".

## Captured examples

Captured with curl from the running app on 13 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out. The `Authorization` header carries this station's demo passwords.

### Case 1: Asha adds Ravi

**Why:** valid fields, a known IFSC, not a duplicate: `201`. Only the last 4 digits of the account come back. The headers Spring Security adds (`Cache-Control`, `X-Frame-Options` and others) are visible here.

Request

``` code
POST /beneficiaries HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "name": "Ravi Menon",
  "accountNumber": "50100123457890",
  "ifsc": "HDFC0001234"
}
```

Response

``` code
HTTP/1.1 201 
Location: /beneficiaries/4ac7e2db-782c-4453-b3ed-81381e897ebe
X-Content-Type-Options: nosniff
X-XSS-Protection: 0
Cache-Control: no-cache, no-store, max-age=0, must-revalidate
Pragma: no-cache
Expires: 0
X-Frame-Options: DENY
Content-Type: application/json

{
  "id": "4ac7e2db-782c-4453-b3ed-81381e897ebe",
  "name": "Ravi Menon",
  "accountNumberMasked": "XXXXXXXXXX7890",
  "ifsc": "HDFC0001234",
  "bankBranch": "HDFC Bank, Koramangala, Bengaluru",
  "createdAt": "2026-10-13T13:53:04.961Z"
}
```

### Case 2: a script tag as the name

**Why:** three fields break their rules: three messages. None repeats the input, so the `<script>` never comes back.

Request

``` code
POST /beneficiaries HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "name": "<script>alert(1)</script>",
  "accountNumber": "12AB",
  "ifsc": "HDFC1234"
}
```

Response

``` code
HTTP/1.1 400 
X-Content-Type-Options: nosniff
X-XSS-Protection: 0
Cache-Control: no-cache, no-store, max-age=0, must-revalidate
Pragma: no-cache
Expires: 0
X-Frame-Options: DENY
Content-Type: application/problem+json

{
  "detail": "Some fields are invalid.",
  "instance": "/beneficiaries",
  "status": 400,
  "title": "Invalid request",
  "type": "https://tijori.example/problems/invalid-request",
  "errors": {
    "accountNumber": "must be 9 to 18 digits",
    "ifsc": "must be 11 characters like HDFC0001234",
    "name": "must be 2-100 letters, spaces, dots, apostrophes or hyphens"
  }
}
```

### Case 3: a well-formed IFSC that no branch has

**Why:** the shape is right, the branch does not exist: `400` with its own type, so the app can say "check the IFSC".

Request

``` code
POST /beneficiaries HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "name": "Ravi Menon",
  "accountNumber": "50100123457891",
  "ifsc": "ABCD0123456"
}
```

Response

``` code
HTTP/1.1 400 
X-Content-Type-Options: nosniff
X-XSS-Protection: 0
Cache-Control: no-cache, no-store, max-age=0, must-revalidate
Pragma: no-cache
Expires: 0
X-Frame-Options: DENY
Content-Type: application/problem+json

{
  "detail": "No bank branch has this IFSC. Check the code printed on a cheque or the bank's website.",
  "instance": "/beneficiaries",
  "status": 400,
  "title": "Unknown IFSC",
  "type": "https://tijori.example/problems/unknown-ifsc"
}
```

### Case 4: the same account again

**Why:** `409`, and the body names the beneficiary that already exists.

Request

``` code
POST /beneficiaries HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "name": "Ravi Menon",
  "accountNumber": "50100123457890",
  "ifsc": "HDFC0001234"
}
```

Response

``` code
HTTP/1.1 409 
X-Content-Type-Options: nosniff
X-XSS-Protection: 0
Cache-Control: no-cache, no-store, max-age=0, must-revalidate
Pragma: no-cache
Expires: 0
X-Frame-Options: DENY
Content-Type: application/problem+json

{
  "detail": "This account at this branch is already one of your beneficiaries.",
  "instance": "/beneficiaries",
  "status": 409,
  "title": "Already a beneficiary",
  "type": "https://tijori.example/problems/duplicate-beneficiary",
  "existingBeneficiaryId": "4ac7e2db-782c-4453-b3ed-81381e897ebe"
}
```

### Case 5: Ravi asks for Asha's beneficiary

**Why:** `404`, word for word what an unknown id gets. Ravi cannot tell that the id exists.

Request

``` code
GET /beneficiaries/4ac7e2db-782c-4453-b3ed-81381e897ebe HTTP/1.1
Authorization: Basic cmF2aTpyYXZpLWRlbW8tcGFzcw==
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
  "detail": "No beneficiary with this id on your account.",
  "instance": "/beneficiaries/4ac7e2db-782c-4453-b3ed-81381e897ebe",
  "status": 404,
  "title": "Beneficiary not found",
  "type": "https://tijori.example/problems/beneficiary-not-found"
}
```

### Case 6: no credentials

**Why:** `401` from Spring Security's filter, in the same shape, with a `WWW-Authenticate` challenge.

Request

``` code
GET /beneficiaries/4ac7e2db-782c-4453-b3ed-81381e897ebe HTTP/1.1
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
Content-Length: 214

{
  "type": "https://tijori.example/problems/unauthenticated",
  "title": "Sign-in required",
  "status": 401,
  "detail": "Send valid credentials to use this API.",
  "instance": "/beneficiaries/4ac7e2db-782c-4453-b3ed-81381e897ebe"
}
```

### Case 7: Meera, a viewer, tries to add

**Why:** she is signed in but may only read: `403`.

Request

``` code
POST /beneficiaries HTTP/1.1
Authorization: Basic bWVlcmE6bWVlcmEtZGVtby1wYXNz
Content-Type: application/json

{
  "name": "Ravi Menon",
  "accountNumber": "50100123457892",
  "ifsc": "HDFC0001234"
}
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
Content-Length: 155

{
  "type": "https://tijori.example/problems/forbidden",
  "title": "Not allowed",
  "status": 403,
  "detail": "Your account cannot do this.",
  "instance": "/beneficiaries"
}
```

### Case 8: SQL where an id belongs

**Why:** `400` naming the parameter, not its value. Spring's default message would have repeated the SQL (see Edge cases).

Request

``` code
GET /beneficiaries/1'%20OR%20'1'='1 HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 400 
X-Content-Type-Options: nosniff
X-XSS-Protection: 0
Cache-Control: no-cache, no-store, max-age=0, must-revalidate
Pragma: no-cache
Expires: 0
X-Frame-Options: DENY
Content-Type: application/problem+json

{
  "detail": "'id' has the wrong format.",
  "instance": "/beneficiaries/1'%20OR%20'1'='1",
  "status": 400,
  "title": "Invalid request",
  "type": "https://tijori.example/problems/invalid-request"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                        | What the API does                              | Proved by                                                                                   |
|-------------------------------------------------------------|------------------------------------------------|---------------------------------------------------------------------------------------------|
| Valid beneficiary                                           | `201`, masked account, readable `Location`     | `addingIs201WithLocationAndOnlyTheLast4DigitsOfTheAccount`, `theOwnerCanReadItBack`         |
| Lower-case IFSC                                             | Accepted, stored upper case                    | `aLowerCaseIfscIsAccepted`                                                                  |
| Fields break rules                                          | `400` `invalid-request`, one message each      | `invalidFieldsAre400WithOneMessagePerField`                                                 |
| Unknown IFSC                                                | `400` `unknown-ifsc`                           | `aWellFormedButUnknownIfscIs400WithItsOwnType`                                              |
| IFSC directory down                                         | `503` + `Retry-After`; internal host not shown | `anIfscDirectoryOutageIs503WithRetryAfterNotA400`                                           |
| Duplicate                                                   | `409` with `existingBeneficiaryId`             | `theSameAccountTwiceIs409NamingTheExistingBeneficiary`                                      |
| Unknown id                                                  | `404`                                          | `anUnknownIdIs404`                                                                          |
| Broken JSON, unknown path, wrong method, wrong content type | Same problem shape                             | `brokenJsonIs400InTheSameShape`, `unknownPathsAndWrongMethodsAreProblemsToo`                |
| Any error at all                                            | No exception names, no stack trace             | `noErrorEverCarriesAnExceptionNameOrAStackTrace`                                            |
| Database failure inside the app                             | `500` with `errorId` only                      | `theRealApiAnswersWithAProblemAndAnErrorIdOnly`                                             |
| No credentials; wrong password                              | `401`, identical bodies                        | `noCredentialsIs401ProblemWithAChallenge`, `aWrongPasswordGetsTheSameAnswerAsNoCredentials` |
| Viewer adds                                                 | `403`                                          | `aViewerCannotAddBeneficiaries403`                                                          |
| Another customer's beneficiary                              | `404`, identical to unknown                    | `anotherCustomersBeneficiaryLooksExactlyLikeOneThatDoesNotExist`                            |
| `owner` field in the body                                   | Ignored; the owner is the signed-in user       | `anOwnerFieldInTheBodyIsIgnored`                                                            |
| Script tag in the name                                      | `400`; never echoed                            | `aScriptInTheNameIsRejectedAndNeverEchoed`                                                  |
| SQL in the path                                             | `400`; never echoed                            | `sqlInThePathIs400AndIsNotEchoed`                                                           |

## The trap

Plausible but wrong

Returning exception messages and stack traces, leaking internals to attackers.

"Show the real error, it helps debugging" is how it starts. The first test makes the store fail with a realistic message and calls a "before" controller whose handler returns `e.getMessage()` and the stack trace: the response contains the database host, the SQL and the code's class names. The second test causes the same failure in the real API: a problem with an `errorId`, and none of those strings.

``` code
package com.tijori.beneficiaries;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.io.PrintWriter;
import java.io.StringWriter;
import java.security.Principal;
import java.util.Map;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.not;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: it reproduces the leak before the fix.
 * Saving fails deep inside the app with a message that names the database host and the SQL.
 */
@Import(LeakyErrorsTrapTest.NaiveController.class)
class LeakyErrorsTrapTest extends ApiTest {

    static final String INTERNAL = "Connection to 10.0.3.17:5432 refused while running INSERT INTO beneficiaries (owner, account_number)";

    @MockitoSpyBean
    BeneficiaryStore store;

    /** The "before" code: a handler that sends the exception's message and stack trace back to the caller. */
    @RestController
    static class NaiveController {
        private final BeneficiaryService service;

        NaiveController(BeneficiaryService service) {
            this.service = service;
        }

        @PostMapping("/naive/beneficiaries")
        BeneficiaryView add(Principal p, @RequestBody BeneficiaryRequest r) {
            return service.add(p.getName(), r);
        }

        @ExceptionHandler(Exception.class)
        org.springframework.http.ResponseEntity<Map<String, String>> error(Exception e) {
            StringWriter trace = new StringWriter();
            e.printStackTrace(new PrintWriter(trace));
            return org.springframework.http.ResponseEntity.internalServerError()
                    .body(Map.of("error", e.getMessage(), "trace", trace.toString()));
        }
    }

    @Test
    void theNaiveHandlerHandsAttackersTheDatabaseHostTheSqlAndTheCodeLayout() throws Exception {
        doThrow(new IllegalStateException(INTERNAL)).when(store).save(any());
        mvc.perform(post("/naive/beneficiaries").with(httpBasic("asha", "asha-demo-pass"))
                        .contentType("application/json").content(ravisAccount()))
                .andExpect(status().isInternalServerError())
                .andExpect(content().string(containsString("10.0.3.17:5432")))                 // internal network address
                .andExpect(content().string(containsString("INSERT INTO beneficiaries")))     // table and column names
                .andExpect(content().string(containsString("at com.tijori.beneficiaries.")));  // class names and line numbers
    }

    @Test
    void theRealApiAnswersWithAProblemAndAnErrorIdOnly() throws Exception {
        doThrow(new IllegalStateException(INTERNAL)).when(store).save(any());
        add("asha", ravisAccount())
                .andExpect(status().isInternalServerError())
                .andExpect(content().contentType("application/problem+json"))
                .andExpect(jsonPath("$.type").value("https://tijori.example/problems/internal-error"))
                .andExpect(jsonPath("$.title").value("Something went wrong"))
                .andExpect(jsonPath("$.errorId").isNotEmpty())
                .andExpect(content().string(not(containsString("10.0.3.17"))))
                .andExpect(content().string(not(containsString("INSERT"))))
                .andExpect(content().string(not(containsString("com.tijori"))));
    }
}
```

### A leak the tests found in Spring's defaults

While building this station, `sqlInThePathIs400AndIsNotEchoed` failed. For `GET /beneficiaries/1' OR '1'='1`, Spring's built-in handler answered with `"detail": "Failed to convert 'id' with value: '1' OR '1'='1'"`, repeating the attacker's text back. `ApiErrors` now overrides `handleTypeMismatch` to name the parameter only. The test was red before the override and green after. Framework defaults are a good start, not a guarantee.

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
./mvnw test                 # all 20 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Demo users: `asha` / `asha-demo-pass` and `ravi` / `ravi-demo-pass` (customers), `meera` / `meera-demo-pass` (viewer). The body is in `docs/beneficiary.json`.

``` code
# Add: expect 201 and a masked account number
curl -i -u asha:asha-demo-pass -X POST http://localhost:8080/beneficiaries -H "Content-Type: application/json" -d "@docs/beneficiary.json"

# The same again: expect 409 duplicate-beneficiary
curl -i -u asha:asha-demo-pass -X POST http://localhost:8080/beneficiaries -H "Content-Type: application/json" -d "@docs/beneficiary.json"

# As a viewer: expect 403 forbidden
curl -i -u meera:meera-demo-pass -X POST http://localhost:8080/beneficiaries -H "Content-Type: application/json" -d "@docs/beneficiary.json"

# Without credentials: expect 401 unauthenticated
curl -i http://localhost:8080/beneficiaries/00000000-0000-0000-0000-000000000000
```

Then stop the app and look at its console after the `500` test: the log line holds the `errorId` and the full exception, which the response did not.

## Troubleshooting

| You see                            | Cause                                   | Fix                                                      |
|------------------------------------|-----------------------------------------|----------------------------------------------------------|
| `401` for every request            | Missing or mistyped `-u user:password`. | Use the demo users above.                                |
| `403` on `POST`                    | Signed in as `meera`, a viewer.         | Use `asha` or `ravi`.                                    |
| `release version 25 not supported` | Maven is using an older JDK.            | Point `JAVA_HOME` at JDK 25, or add `-Djava.version=21`. |

## Project layout

``` tree
stations/006-one-error-shape-for-a-banking-api/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tijori/beneficiaries/
│   ├── SecurityConfig.java        ├── ProblemResponses.java
│   ├── BeneficiaryController.java ├── BeneficiaryRequest.java
│   ├── BeneficiaryService.java    ├── Exceptions.java
│   ├── ApiErrors.java             ├── IfscDirectory.java
│   ├── BeneficiaryStore.java      ├── Beneficiary.java, BeneficiaryView.java
│   └── BeneficiariesApplication.java
├── src/test/java/com/tijori/beneficiaries/   (see Tests)
├── review/                   the flawed version (see Review)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels: security filters first, then the controller, the service, and the error mapping on the way out.

#### `src/main/java/com/tijori/beneficiaries/SecurityConfig.java`

Does  
Requires sign-in for everything, lets only customers add, and points 401 and 403 at `ProblemResponses`.

Why  
Security runs as servlet filters before any controller; this is where its errors are shaped.

Without it  
Spring Security's default 401 has an empty body and its 403 another format: two more shapes for the app to handle.

- CSRF protection is off because nothing uses cookies or sessions: credentials travel with every request.
- Passwords are stored as bcrypt hashes even in this demo.

#### `src/main/java/com/tijori/beneficiaries/ProblemResponses.java`

Does  
Writes the 401 and 403 problem bodies by hand.

Why  
`@RestControllerAdvice` only sees exceptions from controllers; these happen earlier.

Without it  
Sign-in errors would not match the rest.

#### `src/main/java/com/tijori/beneficiaries/BeneficiaryController.java`

Does  
Two endpoints. No `try`/`catch`: failures are exceptions.

Why  
Error handling in one place means one shape.

Without it  
No API.

- The owner comes from `Principal`, the signed-in user, never from the body.

#### `src/main/java/com/tijori/beneficiaries/BeneficiaryRequest.java`

Does  
The body's rules. Messages state the rule, not the value.

Why  
Rules apply to every client.

Without it  
Anything is stored.

#### `src/main/java/com/tijori/beneficiaries/BeneficiaryService.java`

Does  
The business rules: check the IFSC, refuse duplicates, save; find only the owner's beneficiaries.

Why  
It throws exceptions that say what happened in business terms, and knows nothing about HTTP.

Without it  
Status codes would be chosen in many places.

- An exception from the directory becomes `IfscDirectoryUnavailable` (503); an empty answer becomes `UnknownIfsc` (400). Mixing these up is one of the Review findings.

#### `src/main/java/com/tijori/beneficiaries/Exceptions.java`

Does  
The four business exceptions.

Why  
Each names one situation the client can act on.

Without it  
Everything would be a generic exception and a 500.

#### `src/main/java/com/tijori/beneficiaries/ApiErrors.java`

Does  
Maps every exception to a status and a problem type; logs unexpected ones with an `errorId`.

Why  
One place decides the error contract for the whole API.

Without it  
Each controller invents its own error format (the business problem).

- `unexpected(Exception)` is the safety net: it is chosen only when no more specific handler matches.
- `handleTypeMismatch` stops Spring's default message from echoing input.

#### `src/main/java/com/tijori/beneficiaries/IfscDirectory.java`

Simulated IFSC lookup: four branches in a map.

#### `src/main/java/com/tijori/beneficiaries/BeneficiaryStore.java`

Beneficiaries in a `ConcurrentHashMap`.

#### `src/main/java/com/tijori/beneficiaries/Beneficiary.java`

The stored record, with `view()` to mask the account number.

#### `src/main/java/com/tijori/beneficiaries/BeneficiaryView.java`

The response body.

#### `src/main/resources/application.yaml`

States Spring Boot's safe defaults for error pages explicitly: no stack traces, no messages.

#### `pom.xml`

Adds `spring-boot-starter-security`, and `spring-boot-starter-security-test` for `httpBasic(...)` in tests.

# 2 · Build: Tests

## Required tests for this station

Station type: Security

| Required by   | Requirement                                                 | Test class                     | Result |
|---------------|-------------------------------------------------------------|--------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                    | `BeneficiaryContractTest` (11) | pass   |
| Every station | Reproduce the failure before the fix                        | `LeakyErrorsTrapTest` (2)      | pass   |
| Security      | 401, 403, one user reaching another's data, malicious input | `BeneficiarySecurityTest` (7)  | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, Spring Security 7. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.beneficiaries.LeakyErrorsTrapTest
[INFO] Tests run: 11, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.beneficiaries.BeneficiaryContractTest
[INFO] Tests run: 7, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.beneficiaries.BeneficiarySecurityTest
[INFO] Tests run: 20, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/tijori/beneficiaries/LeakyErrorsTrapTest.java`

Written first: the leaky handler hands out host, SQL and class names; the real API hands out an `errorId`.

#### `src/test/java/com/tijori/beneficiaries/BeneficiaryContractTest.java`

Every status code and problem type, the 503 with a simulated outage, and a sweep that no error carries an exception name.

#### `src/test/java/com/tijori/beneficiaries/BeneficiarySecurityTest.java`

401 (and the same body for a wrong password), 403, cross-customer 404, the owner field ignored, script and SQL never echoed.

#### `src/test/java/com/tijori/beneficiaries/ApiTest.java`

Shared setup: the whole app with its security filters, through MockMvc with real Basic headers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/tijori/beneficiaries/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=DeleteBeneficiaryChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 20 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 26 tests pass (20 station tests and 6 challenge tests).

Challenge 1 · Beginner-friendly · about 30 minutes

## Delete a beneficiary

Add `DELETE /beneficiaries/{id}`: `204` for the owner; `404` (in the usual shape) for another customer's beneficiary; `403` for a viewer.

**Done when:** all three tests in `DeleteBeneficiaryChallengeTest` pass, and the station's tests still pass.

Hints

- Reuse `get(owner, id)` in the service, so delete follows exactly the same ownership rule.
- The `403` belongs in `SecurityConfig`, next to the rule for `POST`.
- No new error handling should be needed: the existing exceptions already map to the right problems.

#### `challenge/DeleteBeneficiaryChallengeTest.java`

``` code
package com.tijori.beneficiaries;

import org.junit.jupiter.api.Test;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: DELETE /beneficiaries/{id}, with the same error shape and the same ownership rule as GET. */
class DeleteBeneficiaryChallengeTest extends ApiTest {

    @Test
    void theOwnerDeletesIt204AndItIsGone() throws Exception {
        String location = add("asha", ravisAccount()).andReturn().getResponse().getHeader("Location");
        mvc.perform(delete(location).with(httpBasic("asha", "asha-demo-pass"))).andExpect(status().isNoContent());
        mvc.perform(get(location).with(httpBasic("asha", "asha-demo-pass"))).andExpect(status().isNotFound());
    }

    @Test
    void anotherCustomerCannotDeleteItAndLearnsNothing() throws Exception {
        String location = add("asha", ravisAccount()).andReturn().getResponse().getHeader("Location");
        mvc.perform(delete(location).with(httpBasic("ravi", "ravi-demo-pass")))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.type").value("https://tijori.example/problems/beneficiary-not-found"));
        mvc.perform(get(location).with(httpBasic("asha", "asha-demo-pass"))).andExpect(status().isOk());
    }

    @Test
    void aViewerCannotDelete403() throws Exception {
        String location = add("asha", ravisAccount()).andReturn().getResponse().getHeader("Location");
        mvc.perform(delete(location).with(httpBasic("meera", "meera-demo-pass")))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.type").value("https://tijori.example/problems/forbidden"));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 45 minutes

## A request id in every error

Support asks customers for an id they can search the logs with. Read `X-Request-Id` from the request (keep it only if it is 8–64 letters, digits or hyphens; otherwise make a UUID), return it as a response header, and add it as `requestId` to every problem, including 401s.

**Done when:** all three tests in `RequestIdChallengeTest` pass.

Hints

- A servlet filter with `@Order(Ordered.HIGHEST_PRECEDENCE)` runs before Spring Security's filters.
- Never echo an id you have not checked: that is the same leak as the station's trap.
- Problems are built in three places: `ApiErrors` handlers, Spring's own handlers (`createResponseEntity`), and `ProblemResponses`.
- `MDC.put("requestId", id)` puts it on every log line of the request.

#### `challenge/RequestIdChallengeTest.java`

``` code
package com.tijori.beneficiaries;

import org.junit.jupiter.api.Test;

import java.util.UUID;

import static org.hamcrest.Matchers.matchesPattern;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: every response carries a request id, and every problem body repeats it, so support can find the log lines. */
class RequestIdChallengeTest extends ApiTest {

    @Test
    void aValidRequestIdFromTheAppIsKeptInTheHeaderAndTheProblem() throws Exception {
        mvc.perform(get("/beneficiaries/{id}", UUID.randomUUID()).with(httpBasic("asha", "asha-demo-pass"))
                        .header("X-Request-Id", "app-7f3c9a2e-0001"))
                .andExpect(status().isNotFound())
                .andExpect(header().string("X-Request-Id", "app-7f3c9a2e-0001"))
                .andExpect(jsonPath("$.requestId").value("app-7f3c9a2e-0001"));
    }

    @Test
    void anUnsafeRequestIdIsReplacedNotEchoed() throws Exception {
        mvc.perform(get("/beneficiaries/{id}", UUID.randomUUID()).with(httpBasic("asha", "asha-demo-pass"))
                        .header("X-Request-Id", "<script>x</script>"))
                .andExpect(header().string("X-Request-Id", matchesPattern("[0-9a-f-]{36}")))
                .andExpect(jsonPath("$.requestId", matchesPattern("[0-9a-f-]{36}")));
    }

    @Test
    void securityErrorsCarryItToo() throws Exception {
        mvc.perform(get("/beneficiaries/{id}", UUID.randomUUID()).header("X-Request-Id", "app-7f3c9a2e-0002"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.requestId").value("app-7f3c9a2e-0002"));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Error messages in Hindi and Tamil

Tijori's app is used in five languages. Should the API translate `title` and `detail` (using `Accept-Language`), or should the app translate based on `type`? What happens to log searches and support tickets in each case? Which fields must never be translated?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: a leaky handler shows host, SQL and class names.
2.  List every error the client can act on; give each an exception, a status and a type.
3.  Write one `@RestControllerAdvice`; add a catch-all that logs with an `errorId`.
4.  Make Spring Security's 401 and 403 write the same shape.
5.  Test that nothing is echoed: scripts, SQL, internal hostnames.

## Design alternatives and trade-offs

| Approach                                                  | What it costs                                                           | Verdict             |
|-----------------------------------------------------------|-------------------------------------------------------------------------|---------------------|
| Business exceptions + one advice + `ProblemDetail`        | A small exception class per situation.                                  | Chosen              |
| Return `e.getMessage()` and the stack trace               | Hands attackers internal hosts, SQL and code layout.                    | Wrong               |
| `try`/`catch` in every controller                         | Each one drifts into its own format.                                    | Wrong               |
| `ErrorResponseException` thrown directly from the service | Less code (stations 001–005 did this), but the service then knows HTTP. | Fine for small APIs |
| A custom error JSON instead of RFC 9457                   | Works, but every client and tool must learn yours.                      | Possible            |
| 403 for another customer's beneficiary                    | Confirms the id exists.                                                 | Leaks               |

## Database design

None in this station. When a database arrives, its exceptions (constraint violations, timeouts) get their own mapping: a unique-constraint violation becomes the same `409`, a timeout a `503`, and anything else the `500` with an `errorId`.

# 3 · Go deeper: Production

Security  
No stack traces, no exception messages, no echoed input, no "it exists but is not yours". Account numbers are masked. Demo passwords live in code only because this is a demo. One field does repeat the request: `instance` is the path that was called, URL-encoded (case 8 shows `%20` for spaces). It is JSON data for the caller's own request; an app that shows it must still escape it as text.

Operations  
The `errorId` joins a customer's complaint to the exact log line. Count `500`s by `type`; alert when `internal-error` rises, because each one is a bug.

Reliability  
`503` with `Retry-After` tells well-behaved clients to wait instead of hammering a struggling dependency.

Maintainability  
A new error is a new exception and one handler method. The error catalogue in the API tab is the contract; changing a `type` breaks clients.

# 3 · Go deeper: Interview

## Interview takeaways

Why not return the exception message to the client?

It is written for developers and can contain anything: SQL, hostnames, file paths, customer data. Log it with an id, and return only the id and a safe description.

What is RFC 9457 and why use it?

A standard JSON format for HTTP API errors (it replaced RFC 7807): type, title, status, detail, instance, plus your own fields. Clients and tools already understand it, and Spring supports it with ProblemDetail.

400, 404, 409 or 503: how do you choose?

By what the client should do next. 400: fix the request. 404: the thing is not there (for you). 409: it clashes with the current state (already exists). 503: nothing is wrong with your request, try later.

Why does @RestControllerAdvice not handle 401 and 403?

Spring Security rejects those requests in servlet filters, before Spring MVC and its controllers run. You shape them with an AuthenticationEntryPoint and an AccessDeniedHandler.

Another customer's resource: 403 or 404?

404, identical to a missing one. 403 confirms the id exists, which helps an attacker enumerate valid ids.

Framework default error handling is safe, right?

Mostly. In this station Spring's default type-mismatch message echoed the request value back. Test your error responses for echoed input; do not assume.

## Self-check rubric

| Area        | Meets the bar                                           | Above the bar                                                       |
|-------------|---------------------------------------------------------|---------------------------------------------------------------------|
| Correctness | All 20 tests pass.                                      | You can predict which tests the flawed version fails, and why.      |
| Security    | Nothing internal or echoed in any error.                | You found another place where input could be echoed, and tested it. |
| Design      | One advice; a type per error the client can act on.     | You can defend 404 over 403 for other customers' data.              |
| Explanation | You can walk an exception from the service to the JSON. | You can explain why 401 is shaped somewhere else.                   |

# 3 · Go deeper: Review

## The pull request

A teammate "cleaned up" error handling. Every error is a `ProblemDetail` now, and the happy-path tests pass. Read both files and list every problem before opening the findings.

#### `review/ApiErrors.java`

``` code
package com.tijori.beneficiaries;

import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.context.request.WebRequest;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;

import java.net.URI;
import java.util.Map;
import java.util.TreeMap;

/** Centralised error handling: every error is a ProblemDetail. */
@RestControllerAdvice
class ApiErrors extends ResponseEntityExceptionHandler {

    static final String TYPES = "https://tijori.example/problems/";

    static ProblemDetail problem(HttpStatus status, String type, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setType(URI.create(TYPES + type));
        p.setTitle(title);
        return p;
    }

    @ExceptionHandler
    ResponseEntity<ProblemDetail> notFound(Exceptions.BeneficiaryNotFound e) {
        return respond(problem(HttpStatus.NOT_FOUND, "beneficiary-not-found", "Beneficiary not found",
                "No beneficiary with this id on your account."));
    }

    @ExceptionHandler
    ResponseEntity<ProblemDetail> duplicate(Exceptions.DuplicateBeneficiary e) {
        ProblemDetail p = problem(HttpStatus.CONFLICT, "duplicate-beneficiary", "Already a beneficiary",
                "This account at this branch is already one of your beneficiaries.");
        p.setProperty("existingBeneficiaryId", e.existingId);
        return respond(p);
    }

    /** Both are IFSC problems, so one handler keeps it simple. */
    @ExceptionHandler({Exceptions.UnknownIfsc.class, Exceptions.IfscDirectoryUnavailable.class})
    ResponseEntity<ProblemDetail> ifsc(RuntimeException e) {
        return respond(problem(HttpStatus.BAD_REQUEST, "unknown-ifsc", "Unknown IFSC",
                "We could not verify this IFSC. Please check it and try again."));
    }

    /** Helpful for debugging: the client sees what went wrong. */
    @ExceptionHandler
    ResponseEntity<ProblemDetail> unexpected(Exception e) {
        return respond(problem(HttpStatus.INTERNAL_SERVER_ERROR, "internal-error", "Something went wrong", e.getMessage()));
    }

    /** Shows the user exactly which value was wrong. */
    @Override
    protected ResponseEntity<Object> handleMethodArgumentNotValid(
            MethodArgumentNotValidException ex, HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        Map<String, String> errors = new TreeMap<>();
        ex.getBindingResult().getFieldErrors().forEach(f ->
                errors.putIfAbsent(f.getField(), "'" + f.getRejectedValue() + "' " + f.getDefaultMessage()));
        ProblemDetail p = problem(HttpStatus.BAD_REQUEST, "invalid-request", "Invalid request", "Some fields are invalid.");
        p.setProperty("errors", errors);
        return handleExceptionInternal(ex, p, headers, status, request);
    }

    private static ResponseEntity<ProblemDetail> respond(ProblemDetail p) {
        return ResponseEntity.status(p.getStatus()).body(p);
    }
}
```

#### `review/BeneficiaryService.java`

``` code
package com.tijori.beneficiaries;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Optional;
import java.util.UUID;

/** The rules. It throws business exceptions and knows nothing about HTTP. */
@Service
class BeneficiaryService {

    private final IfscDirectory directory;
    private final BeneficiaryStore store;

    BeneficiaryService(IfscDirectory directory, BeneficiaryStore store) {
        this.directory = directory;
        this.store = store;
    }

    /** synchronized: the duplicate check and the save must not interleave with another request from the same customer. */
    synchronized BeneficiaryView add(String owner, BeneficiaryRequest r) {
        Optional<String> found;
        try {
            found = directory.branch(r.ifsc());
        } catch (RuntimeException e) {
            throw new Exceptions.IfscDirectoryUnavailable(e); // an outage is not the customer's mistake: 503, not 400
        }
        String branch = found.orElseThrow(Exceptions.UnknownIfsc::new);
        store.findSame(owner, r.accountNumber(), r.ifsc()).ifPresent(existing -> {
            throw new Exceptions.DuplicateBeneficiary(existing.id());
        });
        var b = new Beneficiary(UUID.randomUUID(), owner, r.name(), r.accountNumber(), r.ifsc(), branch,
                Instant.now().truncatedTo(ChronoUnit.MILLIS));
        return store.save(b).view();
    }

    /** Clear errors: 404 if it does not exist, 403 if it belongs to someone else. */
    BeneficiaryView get(String owner, UUID id) {
        Beneficiary b = store.find(id).orElseThrow(() -> new Exceptions.BeneficiaryNotFound(id));
        if (!b.owner().equals(owner)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "This beneficiary belongs to another customer");
        }
        return b.view();
    }
}
```

## Findings

1The catch-all handler returns `e.getMessage()`

"Helpful for debugging": the database host and the SQL from the store's exception go straight to the client.

**Test evidence:** `theRealApiAnswersWithAProblemAndAnErrorIdOnly`: no `errorId`, because the `detail` is the store's message, database host and SQL included.

2Validation messages repeat the rejected value

`'<script>…' must be…` sends the attacker's script back. If any page shows that message as HTML, it runs.

**Test evidence:** `aScriptInTheNameIsRejectedAndNeverEchoed` and `invalidFieldsAre400WithOneMessagePerField`.

3Directory outage mapped to the same 400 as an unknown IFSC

"Both are IFSC problems." The customer is told to fix a correct IFSC while the service is down, and no client retries.

**Test evidence:** `anIfscDirectoryOutageIs503WithRetryAfterNotA400`: got 400.

4403 for another customer's beneficiary

"Clear errors": but it confirms the id exists, and the detail says so in words.

**Test evidence:** `anotherCustomersBeneficiaryLooksExactlyLikeOneThatDoesNotExist` and `anOwnerFieldInTheBodyIsIgnored`: got 403.

5No `handleTypeMismatch` override

Spring's default message for a bad path value repeats the value: SQL comes back in the response.

**Test evidence:** `sqlInThePathIs400AndIsNotEchoed`.

## Same tests, flawed version

From `docs/review-run.txt`: the two flawed files copied over the real ones, then the full suite run.

| Test class                | Fixed version | Flawed version |
|---------------------------|---------------|----------------|
| `BeneficiaryContractTest` | 11 / 11       | 9 / 11         |
| `BeneficiarySecurityTest` | 7 / 7         | 3 / 7          |
| `LeakyErrorsTrapTest`     | 2 / 2         | 1 / 2          |

Every flaw looks like a reasonable choice in isolation ("helpful", "simple", "clear"). The security tests catch them because they ask what an attacker or a confused client would see.
