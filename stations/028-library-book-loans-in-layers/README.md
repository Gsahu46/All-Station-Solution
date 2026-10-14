# Station 028 · Library book loans in layers

Foundations · 0–1 years · Core · Public services · Types: none

Spring Boot 4.1.1 · Java 25 · Spring MVC · controller/service/repository · Mockito · @WebMvcTest · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** A demo library in memory: three members, eight books, three loans. Fines are records; no money is paid or collected.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 13 tests.

# 1 · Understand

## The problem in real life

1.  **The web app gets loan rules**

    "At most 3 books, nothing while a fine is unpaid" is written straight into the web controller.

2.  **A kiosk arrives**

    Its developer copies the rules into the kiosk's controller. A year later someone "simplifies" the copy: the kiosk now lends a 4th book and ignores fines. Nobody notices for months.

3.  **The fix**

    Move every rule into one service. Both the web app and the kiosk call it, so there is one copy of each rule, and changing a rule changes it everywhere.

A rule written twice will, one day, say two different things.

## What are we building?

A lending API with two ways in, the web (`POST /loans`) and a self-service kiosk (`POST /kiosk/checkouts`), plus returns and a member's loans. Every rule is in one service behind both.

## An everyday analogy

A library with a front desk and a self-service machine. Both ask the same librarian's rule book; the machine does not keep its own photocopy that nobody updates.

## How it works in 4 steps

1.  **Controller**: reads the request (ids from the web, card and barcode from the kiosk).
2.  **Service**: finds the member and book, applies every rule, decides.
3.  **Repository**: saves the loan, or the return and its fine.
4.  **Back out**: a refusal becomes the same `409` with a reason, whichever way in was used.

Check yourself: the library changes the limit from 3 books to 5. How many files change?

One line in `LoanService` (and its test). Neither controller knows the limit exists.

## What this station is not

- **No database.** Repositories are interfaces with in-memory implementations; a database version would replace them without changing the service.
- **No sign-in.** Members are named by id or card.
- **No payments.** Fines are recorded; challenge 1 records paying them.

## Key terms

| Term                      | Simple meaning                                                           | Everyday example                                   | In this project                             |
|---------------------------|--------------------------------------------------------------------------|----------------------------------------------------|---------------------------------------------|
| **Controller**            | Turns an HTTP request into a method call, and the answer back into HTTP. | The library's front desk.                          | `LoanController`, `KioskController`         |
| **Service**               | Where the rules live.                                                    | The librarian who knows the lending rules.         | `LoanService`                               |
| **Repository**            | Where records are kept and found.                                        | The card catalogue and the ledger.                 | `MemberRepository` and friends              |
| **Constructor injection** | A class receives what it needs through its constructor.                  | A new librarian is handed the keys on day one.     | `LoanService(members, books, loans, clock)` |
| **Mock**                  | A stand-in object a test controls and checks.                            | A rehearsal with a stand-in actor.                 | `@Mock`, `@MockitoBean`                     |
| **Slice test**            | A test that starts only one layer of the app.                            | Testing the front desk with a cardboard librarian. | `@WebMvcTest`                               |

# 2 · Build: Spec

## Business problem

**City Library** (a fictional public library) lends books through its website and a self-service kiosk. The rules were written into the website's controller and copied into the kiosk's. The copies drifted, so the kiosk enforced different rules from the desk, and members found out first.

## Acceptance criteria

1.  **Given** a member with fewer than 3 books and no fine, **then** a loan for 14 days (`201`), from the web or the kiosk.
2.  **Given** a member with 3 books out, **then** `409` LIMIT_REACHED, from either way in.
3.  **Given** a member with an unpaid fine, **then** `409` UNPAID_FINE, from either way in.
4.  **Given** a book already on loan, **then** `409` BOOK_ON_LOAN.
5.  **Given** a return 5 days late, **then** a fine of ₹25, added to the member; returning twice is `409` ALREADY_RETURNED.
6.  **Given** an unknown member, book, card or loan, **then** `404`; a missing field, `400`.

## Requirements

- Demo rules: 3 books at a time, 14 days per loan, ₹5 per late day, no loans with a fine unpaid.
- Controllers hold no rules; the service holds all of them; repositories only store and find.
- Dependencies arrive through constructors; "today" comes from an injected clock, in India time.
- Kiosk card numbers and barcodes are trimmed and upper-cased with `Locale.ROOT`.

## Learning objectives

- Split an API into controller, service and repository, and say what belongs in each.
- Use constructor injection and repository interfaces.
- Unit-test a service with Mockito mocks.
- Choose between a unit test, a `@WebMvcTest` slice and a full `@SpringBootTest`.

# 2 · Build: API contract

## Endpoints

| Method | Path                  | Purpose                                                       |
|--------|-----------------------|---------------------------------------------------------------|
| `POST` | `/loans`              | Borrow: `{"memberId", "bookId"}`. `201`.                      |
| `POST` | `/loans/{id}/return`  | Return, with any late fine. `200`.                            |
| `GET`  | `/members/{id}/loans` | A member's loans, by borrowing date.                          |
| `POST` | `/kiosk/checkouts`    | Borrow at the kiosk: `{"cardNumber", "barcode"}`. Same rules. |

## Status codes

| Status | When                                |
|--------|-------------------------------------|
| 201    | Loan made                           |
| 200    | Returned; a member's loans          |
| 400    | A field missing or blank            |
| 404    | No such member, book, card or loan  |
| 409    | A rule said no; `reason` says which |

## Captured examples

Captured with curl from the running app on 14 Oct 2026, in this order, with "today" from the real clock. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: Asha borrows on the web

**Why:** no books out, no fine: lent for 14 days.

Request

``` code
POST /loans HTTP/1.1
Content-Type: application/json

{
  "memberId": "m-1",
  "bookId": "b-1"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 130

{
  "id": "l-560ce61d",
  "memberId": "m-1",
  "bookId": "b-1",
  "borrowedOn": "2026-10-14",
  "dueOn": "2026-10-28",
  "returnedOn": null,
  "finePaise": 0
}
```

### Case 2: Asha borrows at the kiosk

**Why:** card and barcode instead of ids; the same service decides.

Request

``` code
POST /kiosk/checkouts HTTP/1.1
Content-Type: application/json

{
  "cardNumber": "CL-0001",
  "barcode": "LIB100002"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 130

{
  "id": "l-45166669",
  "memberId": "m-1",
  "bookId": "b-2",
  "borrowedOn": "2026-10-14",
  "dueOn": "2026-10-28",
  "returnedOn": null,
  "finePaise": 0
}
```

### Case 3: Asha's loans

**Why:** both loans, whichever way they were made.

Request

``` code
GET /members/m-1/loans HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 263

[
  {
    "id": "l-45166669",
    "memberId": "m-1",
    "bookId": "b-2",
    "borrowedOn": "2026-10-14",
    "dueOn": "2026-10-28",
    "returnedOn": null,
    "finePaise": 0
  },
  {
    "id": "l-560ce61d",
    "memberId": "m-1",
    "bookId": "b-1",
    "borrowedOn": "2026-10-14",
    "dueOn": "2026-10-28",
    "returnedOn": null,
    "finePaise": 0
  }
]
```

### Case 4: Meera tries a 4th book at the kiosk

**Why:** the kiosk that used to allow this now asks the same rule: `409` LIMIT_REACHED.

Request

``` code
POST /kiosk/checkouts HTTP/1.1
Content-Type: application/json

{
  "cardNumber": "CL-0003",
  "barcode": "LIB100003"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Meera Iyer already has 3 books out; the limit is 3.",
  "instance": "/kiosk/checkouts",
  "status": 409,
  "title": "Loan refused",
  "reason": "LIMIT_REACHED"
}
```

### Case 5: Ravi owes ₹20

**Why:** `409` UNPAID_FINE, with the amount.

Request

``` code
POST /loans HTTP/1.1
Content-Type: application/json

{
  "memberId": "m-2",
  "bookId": "b-3"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Ravi Kumar has an unpaid fine of Rs 20.00.",
  "instance": "/loans",
  "status": 409,
  "title": "Loan refused",
  "reason": "UNPAID_FINE"
}
```

### Case 6: a book already on loan

**Why:** one copy, one loan at a time: `409` BOOK_ON_LOAN.

Request

``` code
POST /loans HTTP/1.1
Content-Type: application/json

{
  "memberId": "m-1",
  "bookId": "b-6"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "\"Gitanjali\" is already on loan.",
  "instance": "/loans",
  "status": 409,
  "title": "Loan refused",
  "reason": "BOOK_ON_LOAN"
}
```

### Case 7: Meera returns a book

**Why:** due 15 October; the fine depends on the day it was captured (₹5 a day late).

Request

``` code
POST /loans/l-6/return HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 131

{
  "id": "l-6",
  "memberId": "m-3",
  "bookId": "b-6",
  "borrowedOn": "2026-10-01",
  "dueOn": "2026-10-15",
  "returnedOn": "2026-10-14",
  "finePaise": 0
}
```

### Case 8: an unknown member

**Why:** `404`.

Request

``` code
GET /members/m-9/loans HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No member m-9.",
  "instance": "/members/m-9/loans",
  "status": 404,
  "title": "Not found"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                         | What happens                        | Proved by                                              |
|----------------------------------------------|-------------------------------------|--------------------------------------------------------|
| A loan on 14 October                         | Due 28 October; listed              | `aBookIsLentForFourteenDays`                           |
| Card and barcode with spaces, lower case     | Normalised; lent                    | `theKioskLendsByCardAndBarcode`                        |
| Returned 5 days late                         | ₹25 fine; next loan refused         | `aLateReturnIsFinedFiveRupeesADayAndBlocksTheNextLoan` |
| Returned on time                             | No fine; the book is free again     | `anOnTimeReturnHasNoFineAndFreesTheBook`               |
| Book out; returned twice                     | `409` with the reason               | `refusalsAre409WithAReason`                            |
| Unknown member, book, card, loan; blank body | `404`; `400`                        | `unknownMembersBooksAndLoansAre404AndBadBodiesAre400`  |
| A refused loan                               | Never saved                         | `aRefusedLoanIsNeverSaved`                             |
| Two books out                                | One more is allowed, due in 14 days | `anAllowedLoanIsSavedDueInFourteenDays`                |
| 4 days late                                  | ₹20 added to the member             | `aLateReturnAddsTheFineToTheMember`                    |
| A refusal, through the web layer only        | `409` with the reason               | `aRefusalFromTheServiceBecomesA409WithItsReason`       |
| A blank body, through the web layer only     | `400`; the service is never called  | `anInvalidBodyNeverReachesTheService`                  |

## The trap

Plausible but wrong

Business rules in controllers, copied into a second entry point and drifting.

The first test runs the two inline copies side by side: the web says no, the kiosk says yes, for a 4th book and for a member with a fine. The second sends the same members through the real web API and the real kiosk: the same `409` and the same reason from both. While building, letting the kiosk save loans without the service turned 1 test red, an off-by-one in the limit turned 2 red, and dropping the fine rule turned 2 red.

``` code
package com.citylibrary.loans;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The first test written for this station: it reproduces the bug before the fix. */
class RulesInControllersTrapTest extends ApiTest {

    /** The "before" web controller's rule, written inline. Kept only in tests. */
    static boolean oldWebAllows(int booksOut, long unpaidFinePaise) {
        return unpaidFinePaise == 0 && booksOut < 3;
    }

    /** The kiosk's copy of it, a year later: someone "simplified" it and dropped the fine. Kept only in tests. */
    static boolean oldKioskAllows(int booksOut, long unpaidFinePaise) {
        return booksOut <= 3;
    }

    @Test
    void theCopiesHaveDriftedApart() {
        assertThat(oldWebAllows(3, 0)).isFalse();
        assertThat(oldKioskAllows(3, 0)).isTrue();       // a 4th book at the kiosk
        assertThat(oldWebAllows(0, 2_000)).isFalse();
        assertThat(oldKioskAllows(0, 2_000)).isTrue();   // a loan with a fine unpaid
    }

    @Test
    void theWebAndTheKioskNowGiveTheSameAnswers() throws Exception {
        borrow("m-3", "b-1").andExpect(status().isConflict()).andExpect(jsonPath("$.reason").value("LIMIT_REACHED"));
        kiosk("CL-0003", "LIB100001").andExpect(status().isConflict()).andExpect(jsonPath("$.reason").value("LIMIT_REACHED"));
        borrow("m-2", "b-1").andExpect(status().isConflict()).andExpect(jsonPath("$.reason").value("UNPAID_FINE"));
        kiosk("CL-0002", "LIB100001").andExpect(status().isConflict()).andExpect(jsonPath("$.reason").value("UNPAID_FINE"));
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

Meera has 3 books out. Try both ways in.

``` code
curl -i -X POST http://localhost:8080/loans -H "Content-Type: application/json" -d '{"memberId":"m-3","bookId":"b-1"}'
curl -i -X POST http://localhost:8080/kiosk/checkouts -H "Content-Type: application/json" -d '{"cardNumber":"CL-0003","barcode":"LIB100001"}'
```

## Troubleshooting

| You see                              | Cause                                      | Fix                                                      |
|--------------------------------------|--------------------------------------------|----------------------------------------------------------|
| `409` BOOK_ON_LOAN for b-6, b-7, b-8 | Meera has them out in the demo data.       | Use b-1 to b-5.                                          |
| A fine on the first return           | Meera's books were due on 15 October 2026. | Expected after that date: ₹5 a day.                      |
| `release version 25 not supported`   | Maven is using an older JDK.               | Point `JAVA_HOME` at JDK 25, or add `-Djava.version=21`. |

## Project layout

``` tree
stations/028-library-book-loans-in-layers/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/citylibrary/loans/
│   ├── LoanController.java   ├── KioskController.java   ├── LoanErrors.java      (web layer)
│   ├── LoanService.java                                                          (rules)
│   ├── Repositories.java     ├── InMemoryRepositories.java                       (storage)
│   └── Model.java            └── LibraryApplication.java
├── src/test/java/com/citylibrary/loans/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels: web layer, rules, storage.

#### `src/main/java/com/citylibrary/loans/LoanController.java`

Does  
The web way in: HTTP to service calls and back.

Why  
No rule here, only translation; validation of the body's shape stays at the edge.

Without it  
The trap: the rules written here, then copied.

#### `src/main/java/com/citylibrary/loans/KioskController.java`

Does  
The kiosk way in: card and barcode instead of ids.

Why  
A second controller, the same service: a new way in adds no rules.

Without it  
A kiosk with its own copy of the rules.

#### `src/main/java/com/citylibrary/loans/LoanErrors.java`

One `@RestControllerAdvice` turns the service's refusals and not-founds into problems for both controllers.

#### `src/main/java/com/citylibrary/loans/LoanService.java`

Does  
Every rule, with constructor injection and an injected clock.

Why  
One place to read, change and unit-test the rules.

Without it  
Rules spread across controllers.

- Refusals carry a `Reason`, so every way in explains them the same way.
- `synchronized`: the checks and the save cannot interleave. Safe while one instance runs; across servers, the database must enforce it.

#### `src/main/java/com/citylibrary/loans/Repositories.java`

Does  
The three repository interfaces.

Why  
The service depends on what it needs, not on how it is stored.

Without it  
A service that talks to maps or SQL directly.

#### `src/main/java/com/citylibrary/loans/InMemoryRepositories.java`

In-memory implementations with the demo data. A database version would implement the same interfaces.

#### `src/main/java/com/citylibrary/loans/Model.java`

Members, books and loans as records: data only.

#### `src/main/resources/application.yaml`

Problem bodies for framework errors.

#### `src/main/java/com/citylibrary/loans/LibraryApplication.java`

Entry point, and the clock in India time.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                              | Test class                       | Result |
|---------------|------------------------------------------|----------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found | `LoanContractTest` (6)           | pass   |
| Every station | Reproduce the failure before the fix     | `RulesInControllersTrapTest` (2) | pass   |
| This station  | The rules alone, with Mockito            | `LoanServiceTest` (3)            | pass   |
| This station  | The web layer alone, with @WebMvcTest    | `LoanControllerSliceTest` (2)    | pass   |

## Three kinds of test, side by side

| Test                      | Starts               | Replaces                         | Use it for                                   |
|---------------------------|----------------------|----------------------------------|----------------------------------------------|
| `LoanServiceTest`         | Nothing: plain JUnit | Repositories, with Mockito mocks | Rules: fast, exact, every edge               |
| `LoanControllerSliceTest` | The web layer only   | The service, with `@MockitoBean` | HTTP: status codes, validation, error bodies |
| `LoanContractTest`        | The whole app        | Only the clock                   | That the layers work together                |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.citylibrary.loans.LoanContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.citylibrary.loans.RulesInControllersTrapTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.citylibrary.loans.LoanServiceTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.citylibrary.loans.LoanControllerSliceTest
[INFO] Tests run: 13, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/citylibrary/loans/RulesInControllersTrapTest.java`

Written first: the two drifted copies, and the real web and kiosk agreeing.

#### `src/test/java/com/citylibrary/loans/LoanServiceTest.java`

Mockito mocks for the repositories; checks what the service saves, and what it never saves.

#### `src/test/java/com/citylibrary/loans/LoanControllerSliceTest.java`

`@WebMvcTest` with the service mocked: HTTP only.

#### `src/test/java/com/citylibrary/loans/LoanContractTest.java`

The whole app: borrowing, returning, fines, refusals and not-founds.

#### `src/test/java/com/citylibrary/loans/ApiTest.java`

Shared setup: fresh demo data, and "today" set by each test.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/citylibrary/loans/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=PayFineChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 13 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 17 tests pass (13 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Pay a fine

Add `POST /members/{id}/fine-payments` with `{"amountPaise"}`: part or all of a fine, recorded at the desk. More than is owed is `422`; zero is `400`.

**Done when:** both tests in `PayFineChallengeTest` pass.

Hints

- Controller: one method. Service: the rule (not more than owed). Repository: `save` already exists.
- The advice can map this one refusal to `422` and keep the rest as `409`.

#### `challenge/PayFineChallengeTest.java`

``` code
package com.citylibrary.loans;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: POST /members/{id}/fine-payments with {"amountPaise": 1000} pays part or all of a fine (a record of a
 * payment at the desk; no money moves here). Paying more than is owed is 422. Once paid in full, loans work again.
 */
class PayFineChallengeTest extends ApiTest {

    ResultActions pay(String member, long paise) throws Exception {
        return mvc.perform(post("/members/{id}/fine-payments", member).contentType(MediaType.APPLICATION_JSON)
                .content("{\"amountPaise\":" + paise + "}"));
    }

    @Test
    void payingTheWholeFineLiftsTheBlock() throws Exception {
        pay("m-2", 500).andExpect(status().isOk()).andExpect(jsonPath("$.unpaidFinePaise").value(1_500));
        borrow("m-2", "b-1").andExpect(status().isConflict());
        pay("m-2", 1_500).andExpect(jsonPath("$.unpaidFinePaise").value(0));
        borrow("m-2", "b-1").andExpect(status().isCreated());
    }

    @Test
    void payingTooMuchOrNothingIsRefused() throws Exception {
        pay("m-2", 2_001).andExpect(status().isUnprocessableContent());
        pay("m-2", 0).andExpect(status().isBadRequest());
        pay("m-9", 100).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Renew a loan

Add `POST /loans/{id}/renewals`: 14 more days from the due date, at most twice, never once overdue, never with a fine owed. Every new rule goes in the service.

**Done when:** both tests in `RenewLoanChallengeTest` pass, and the station's tests still pass.

Hints

- The loan needs a renewal count; keep the old record constructor so existing code still compiles.
- Write the new rules as `LoanServiceTest`-style unit tests first: they are the fast ones.

#### `challenge/RenewLoanChallengeTest.java`

``` code
package com.citylibrary.loans;

import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: POST /loans/{id}/renewals adds 14 days to the due date. At most 2 renewals per loan; never once the
 * loan is overdue, and never while the member owes a fine. New rules, so they go in LoanService, nowhere else.
 */
class RenewLoanChallengeTest extends ApiTest {

    ResultActions renew(String loan) throws Exception {
        return mvc.perform(post("/loans/{id}/renewals", loan));
    }

    @Test
    void aLoanCanBeRenewedTwice() throws Exception {
        renew("l-6").andExpect(status().isOk()).andExpect(jsonPath("$.dueOn").value("2026-10-29")).andExpect(jsonPath("$.renewals").value(1));
        renew("l-6").andExpect(jsonPath("$.dueOn").value("2026-11-12")).andExpect(jsonPath("$.renewals").value(2));
        renew("l-6").andExpect(status().isConflict()).andExpect(jsonPath("$.reason").value("RENEWAL_LIMIT"));
    }

    @Test
    void anOverdueLoanCannotBeRenewed() throws Exception {
        today("2026-10-20");
        renew("l-7").andExpect(status().isConflict()).andExpect(jsonPath("$.reason").value("OVERDUE"));
        renew("l-404").andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Where does each rule belong?

For each rule, decide: the entity (a `Loan` knows if it is overdue), the service (the 3-book limit needs other loans), or the database (one active loan per book, as a unique index). Which rules would you enforce in two places, and why is that different from the trap?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the two drifted copies, and the real API from both ways in.
2.  Define the repository interfaces the rules need; implement them in memory.
3.  Move every rule into the service; unit-test it with Mockito.
4.  Thin the controllers to translation; slice-test the web layer; contract-test the whole.

## Design alternatives and trade-offs

| Approach                                  | What it costs                                                               | Verdict            |
|-------------------------------------------|-----------------------------------------------------------------------------|--------------------|
| Rules in a service, thin controllers      | A class and some interfaces.                                                | Chosen             |
| Rules in controllers                      | Every new way in copies them.                                               | The trap           |
| Rules on the entities (rich domain model) | Good for rules about one record; rules across records still need a service. | Mix with a service |
| Spring Data repositories                  | A database; no hand-written implementations.                                | With a database    |
| Field injection (`@Autowired` on fields)  | Hidden dependencies; tests need Spring or reflection.                       | Avoid              |

## Database design

None in this station. With a database: `members`, `books`, `loans` (member, book, borrowed_on, due_on, returned_on, fine_paise), and a unique index on `loans(book_id) WHERE returned_on IS NULL`, so two servers can never lend the same book twice.

# 3 · Go deeper: Production

More ways in  
A mobile app, a staff tool or a batch import each get a controller (or a listener) that calls the same service. None gets its own rules.

Concurrency  
`synchronized` keeps one instance correct. With several instances, the database must enforce "one active loan per book" and the limit inside a transaction.

Testing  
Most tests should be fast service tests; a few slice tests for HTTP; fewer full-app tests to prove the wiring.

Change  
A new rule touches the service and its test. If it touches a controller, it is in the wrong place.

# 3 · Go deeper: Interview

## Interview takeaways

What goes in a controller, a service and a repository?

Controller: HTTP in and out, input shape. Service: business rules and decisions. Repository: storing and finding records. Rules never go in the controller.

Why constructor injection?

Dependencies are explicit and final, the object is complete after construction, and a test can build it with mocks in one line, without Spring.

Why repository interfaces?

The service depends on what it needs, not on how it is stored: an in-memory, JDBC or JPA implementation can be swapped without touching the rules.

Unit test, @WebMvcTest or @SpringBootTest?

Unit tests for rules (fast, precise); @WebMvcTest for HTTP mapping with the service mocked; @SpringBootTest to prove the whole app works together. Most tests should be the first kind.

What does a Mockito mock let you check?

What the code under test asked for and saved: verify(loans, never()).save(any()) proves a refused loan is never stored.

## Self-check rubric

| Area        | Meets the bar                 | Above the bar                                                |
|-------------|-------------------------------|--------------------------------------------------------------|
| Correctness | All 13 tests pass.            | Both ways in give the same answer for every case.            |
| Layers      | No rule in a controller.      | You can say where each rule in challenge 3 belongs.          |
| Testing     | A Mockito test for each rule. | You can choose the right kind of test for a new change.      |
| Explanation | Why rules drift when copied.  | Why a database constraint is still needed with many servers. |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any new endpoint:

- Does the controller decide anything a business person would call a rule?
- Is any rule written in more than one place?
- Are dependencies passed in through the constructor?
- Is there a fast unit test for each rule?
