# Station 032 · Return and refund eligibility

Foundations · 0–1 years · Core · E-commerce · Types: none

Spring Boot 4.1.1 · Java 25 · JUnit 6 parameterized tests · Mockito · AssertJ · fixed Clock · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Orders, prices and return windows are demo data and demo rules, not Kartwala's. The endpoint only answers whether a return would be accepted; nothing is returned, refunded or picked up.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 38 tests.

# 1 · Understand

## The problem in real life

1.  **A rule changes**

    Electronics returns go from 30 days to 7. A developer edits the switch statement, runs the one test (an electronics return on day 3), sees green, and ships.

2.  **Something else breaks**

    Clothing shared that case of the switch. Customers returning a kurta on day 10 are refused. Support finds out from complaints.

3.  **The fix**

    Each category owns its window. The rules become one function tested with a table: every category, every reason, the last day and the day after.

A test suite that checks only what you changed cannot see what you broke.

## What are we building?

`POST /refund-eligibility-checks` answers, before a customer books a pickup: can this order be returned for this reason, how much comes back, and until which day? If not, it lists every reason.

## An everyday analogy

A shop's returns desk with a printed rule card per department. Changing the electronics card cannot change the clothing card, and the manager tests a new card against a list of real situations, not just one.

## How it works in 4 steps

1.  **Find the order** and its category, price and delivery date.
2.  **Find today** in India's calendar.
3.  **Apply the rules**: window, accepted reasons, hygiene items, tags, seal.
4.  **Answer and record**: eligible or every reason why not, the refund, the last day.

Check yourself: the old suite had one test and it passed after the change. What would have caught the bug?

Any test of a clothing return between day 8 and day 30. A table with one row per category at its last day would have turned red the moment clothing's window changed.

## What this station is not

- **No refunds.** A check only: no money moves, no pickup is booked.
- **One item per order.** Real orders have many lines, each checked the same way.
- **No database.** Demo orders in memory.

## Key terms

| Term                   | Simple meaning                                                                               | Everyday example                                        | In this project           |
|------------------------|----------------------------------------------------------------------------------------------|---------------------------------------------------------|---------------------------|
| **Happy path**         | The case where everything goes right.                                                        | Testing a lock only with the right key.                 | electronics, day 3        |
| **Parameterized test** | One test method run once per row of a table of inputs and expected results.                  | A teacher checking every answer against the answer key. | `theRuleTable`            |
| **Pure function**      | Gives the same answer for the same inputs and touches nothing else.                          | A calculator.                                           | `RefundRules.check`       |
| **Stub**               | A stand-in that returns a prepared answer to a question.                                     | A friend reading out a script.                          | `when(orders.find(…))`    |
| **Verify**             | Checking a stand-in was told to do something.                                                | Checking the letter was posted.                         | `verify(audit).record(…)` |
| **Fixed clock**        | A clock that always says the same time, so tests about dates give the same result every day. | A stopped watch in a photo.                             | `Clock.fixed(…)`          |

# 2 · Build: Spec

## Business problem

**Kartwala** (a fictional shopping app) has refund rules with many conditions and no tests but one. A change for electronics broke refunds for clothing, and no test noticed.

## The rules (demo)

| Category    | Window after delivery | Accepted reasons                      | Extra conditions                                                            |
|-------------|-----------------------|---------------------------------------|-----------------------------------------------------------------------------|
| Clothing    | 30 days               | All five                              | Innerwear: only damaged or wrong item. Changed mind or size: tags attached. |
| Electronics | 7 days                | Damaged, wrong item, not as described | Seal broken: only damaged.                                                  |
| Books       | 10 days               | Damaged, wrong item, changed mind     |                                                                             |
| Grocery     | 2 days                | Damaged, wrong item                   |                                                                             |

Changed mind and size issue are the customer's choice: ₹49 pickup fee is deducted. For damaged, wrong or not-as-described items, the full price comes back. Not delivered yet: nothing to return (cancel instead).

## Acceptance criteria

1.  **Given** a kurta delivered 14 days ago that did not fit, tags attached, **then** eligible, ₹1,250.00 back (₹1,299 minus ₹49), last day 16 days from now.
2.  **Given** earbuds delivered 9 days ago, changed mind, seal broken, **then** refused for all three reasons: `WINDOW_CLOSED`, `REASON_NOT_ACCEPTED`, `SEAL_BROKEN`.
3.  **Given** the last day of any category's window, **then** open; the day after, closed.
4.  **Given** 01:30 in India on the day after the last day (still the last day on a UTC server), **then** closed.
5.  **Given** clothing without a `tagsAttached` answer, or electronics without `sealIntact`, **then** `400`.
6.  **Given** an unknown order, `404`; an unknown reason or field, `400`.

## Requirements

- Each category owns its window and reasons; no rule is shared by accident.
- The rules are a pure function; "today" comes from a `Clock`, in India's time zone.
- Every decision is recorded for support.
- Money in integer paise; a refund is never negative.

## Learning objectives

- Write table-driven tests with `@ParameterizedTest`, `@CsvSource` and `@EnumSource`.
- Know when to stub and when to verify with Mockito.
- Use AssertJ for readable assertions.
- Make time testable with a `Clock`.
- Shape code so the important part is easy to test.

# 2 · Build: API contract

## Endpoint

| Method | Path                         | Body                                                                                                                                                   |
|--------|------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| `POST` | `/refund-eligibility-checks` | `{"orderId", "reason", "tagsAttached"?, "sealIntact"?}`. `reason` is one of `DAMAGED`, `WRONG_ITEM`, `NOT_AS_DESCRIBED`, `CHANGED_MIND`, `SIZE_ISSUE`. |

## Status codes

| Status | When                                                                                            |
|--------|-------------------------------------------------------------------------------------------------|
| 200    | A decision: eligible, or refused with every reason                                              |
| 400    | A bad order id, a missing or unknown reason, an unknown field, or a missing tags or seal answer |
| 404    | No such order                                                                                   |

## Captured examples

Captured with curl from the running app on 15 Oct 2026. The demo orders are delivered a fixed number of days before the app starts, so the dates are relative to that day. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: a kurta, day 14, size issue

**Why:** inside 30 days, tags attached. ₹49 pickup fee because it is the customer's choice.

Request

``` code
POST /refund-eligibility-checks HTTP/1.1
Content-Type: application/json

{
  "orderId": "KW-1001",
  "reason": "SIZE_ISSUE",
  "tagsAttached": true
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 102

{
  "orderId": "KW-1001",
  "eligible": true,
  "reasons": [],
  "refundPaise": 125000,
  "lastDayToReturn": "2026-10-31"
}
```

### Case 2: innerwear, changed mind

**Why:** hygiene item: only damaged or wrong items come back.

Request

``` code
POST /refund-eligibility-checks HTTP/1.1
Content-Type: application/json

{
  "orderId": "KW-1002",
  "reason": "CHANGED_MIND",
  "tagsAttached": true
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 112

{
  "orderId": "KW-1002",
  "eligible": false,
  "reasons": [
    "HYGIENE_ITEM"
  ],
  "refundPaise": 0,
  "lastDayToReturn": "2026-11-11"
}
```

### Case 3: earbuds, day 9, changed mind, seal broken

**Why:** three reasons, all listed, so the app can explain them at once.

Request

``` code
POST /refund-eligibility-checks HTTP/1.1
Content-Type: application/json

{
  "orderId": "KW-1003",
  "reason": "CHANGED_MIND",
  "sealIntact": false
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 149

{
  "orderId": "KW-1003",
  "eligible": false,
  "reasons": [
    "WINDOW_CLOSED",
    "REASON_NOT_ACCEPTED",
    "SEAL_BROKEN"
  ],
  "refundPaise": 0,
  "lastDayToReturn": "2026-10-13"
}
```

### Case 4: a phone that arrived damaged

**Why:** the seal is broken, but the reason is damage: full refund.

Request

``` code
POST /refund-eligibility-checks HTTP/1.1
Content-Type: application/json

{
  "orderId": "KW-1004",
  "reason": "DAMAGED",
  "sealIntact": false
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 103

{
  "orderId": "KW-1004",
  "eligible": true,
  "reasons": [],
  "refundPaise": 1899900,
  "lastDayToReturn": "2026-10-20"
}
```

### Case 5: groceries, changed mind

**Why:** groceries come back only if damaged or wrong.

Request

``` code
POST /refund-eligibility-checks HTTP/1.1
Content-Type: application/json

{
  "orderId": "KW-1005",
  "reason": "CHANGED_MIND"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 119

{
  "orderId": "KW-1005",
  "eligible": false,
  "reasons": [
    "REASON_NOT_ACCEPTED"
  ],
  "refundPaise": 0,
  "lastDayToReturn": "2026-10-16"
}
```

### Case 6: a book not yet delivered

**Why:** nothing to return; no last day.

Request

``` code
POST /refund-eligibility-checks HTTP/1.1
Content-Type: application/json

{
  "orderId": "KW-1006",
  "reason": "CHANGED_MIND"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 105

{
  "orderId": "KW-1006",
  "eligible": false,
  "reasons": [
    "NOT_DELIVERED"
  ],
  "refundPaise": 0,
  "lastDayToReturn": null
}
```

### Case 7: KW-9999

**Why:** `404`.

Request

``` code
POST /refund-eligibility-checks HTTP/1.1
Content-Type: application/json

{
  "orderId": "KW-9999",
  "reason": "DAMAGED"
}
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No order KW-9999.",
  "instance": "/refund-eligibility-checks",
  "status": 404,
  "title": "Order not found"
}
```

### Case 8: clothing, no tags answer

**Why:** the rules need it for clothing, so the request is incomplete: `400`.

Request

``` code
POST /refund-eligibility-checks HTTP/1.1
Content-Type: application/json

{
  "orderId": "KW-1001",
  "reason": "SIZE_ISSUE"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "tagsAttached is required for clothing.",
  "instance": "/refund-eligibility-checks",
  "status": 400,
  "title": "Missing answer"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                    | What happens                                               | Proved by                                                |
|---------------------------------------------------------|------------------------------------------------------------|----------------------------------------------------------|
| 17 combinations of category, day, reason, tags and seal | As in the rule table                                       | `theRuleTable`                                           |
| The last day and the day after, every category          | Open, then closed                                          | `theLastDayIsOpenAndTheNextDayIsClosedInEveryCategory`   |
| Innerwear, each reason                                  | Only damaged or wrong item                                 | `hygieneItemsComeBackOnlyWhenItWasOurFault`              |
| Changed mind vs damaged; a ₹30 item with the fee        | ₹49 deducted only for the customer's choice; never below 0 | `theCustomersChoicePaysThePickupFeeAndOurMistakeDoesNot` |
| Not delivered                                           | `NOT_DELIVERED`, no last day                               | `anOrderNotYetDeliveredCannotBeReturned`                 |
| 01:30 in India, 20:00 the day before in UTC             | India's date decides                                       | `theLastDayIsCountedInIndiaNotOnTheServer`               |
| Unknown order; missing answers                          | Nothing recorded                                           | `anUnknownOrderOrAMissingAnswerRecordsNothing`           |
| Unknown reason; missing reason; bad id; extra field     | `400`                                                      | `badRequestsAre400`                                      |

## The trap

Plausible but wrong

Testing only the happy path: one changed rule breaks another category unnoticed.

The test file rebuilds the old switch, where clothing and electronics shared a case. The old suite's only test, an electronics return on day 3, still passes against it. A clothing return on day 20 is refused by it, and accepted by the new rules. While building, each fix was undone once. Clothing back at 7 days turned 5 tests red. Dropping the hygiene rule turned 3 red, and counting days on the server's date instead of India's turned 1 red. Charging the fee for every reason turned 2 red, not recording the decision 1, and letting a broken seal block a damaged phone 2. Listing only the first reason turned 2 red.

``` code
package com.kartwala.refunds;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.assertj.core.api.Assertions.assertThat;

/** The first test written for this station: the old suite had one happy-path test, and it never noticed. */
class HappyPathOnlyTrapTest {

    static final LocalDate TODAY = LocalDate.of(2026, 10, 15);

    @Test
    void theOldSuitesOnlyTestStillPassedAfterTheChange() {
        // The test that existed: electronics, three days after delivery. Green before and after the March change.
        assertThat(OldRefundRules.withinWindow(Category.ELECTRONICS, 3)).isTrue();
    }

    @Test
    void butClothingReturnedOnDay20WasRefusedByTheOldRule() {
        assertThat(OldRefundRules.withinWindow(Category.CLOTHING, 20)).isFalse();   // the bug customers hit
        Order kurta = new Order("KW-1001", "Cotton kurta", Category.CLOTHING, 129_900, TODAY.minusDays(20), false);
        RefundRules.Decision now = RefundRules.check(kurta, Reason.SIZE_ISSUE, true, null, TODAY);
        assertThat(now.eligible()).isTrue();
        assertThat(now.lastDayToReturn()).isEqualTo(TODAY.plusDays(10));
    }

    @Test
    void electronicsKeepsItsSevenDaysSoTheFixDidNotUndoTheChange() {
        Order phone = new Order("KW-1004", "Smartphone", Category.ELECTRONICS, 1_899_900, TODAY.minusDays(8), false);
        assertThat(RefundRules.check(phone, Reason.DAMAGED, null, true, TODAY).reasons()).containsExactly("WINDOW_CLOSED");
    }
}
```

``` code
package com.kartwala.refunds;

/**
 * The window rule as it was before the fix, kept only in tests. Clothing and electronics shared one case of a switch.
 * In March electronics moved from 30 days to 7: the change was made in the shared case, so clothing moved too.
 */
final class OldRefundRules {

    private OldRefundRules() {
    }

    static int windowDays(Category category) {
        switch (category) {
            case CLOTHING:
            case ELECTRONICS:
                return 7;   // was 30 for both; "electronics only" was the intent
            case BOOKS:
                return 10;
            default:
                return 2;
        }
    }

    static boolean withinWindow(Category category, int daysSinceDelivery) {
        return daysSinceDelivery <= windowDays(category);
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
./mvnw spring-boot:run                       # the API on http://localhost:8080
./mvnw test                                  # all 38 tests
./mvnw test -Dtest=RefundRulesTest           # just the rule table, in well under a second
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Make the March mistake: change `CLOTHING(30,` to `CLOTHING(7,` in `Category.java` and run `RefundRulesTest`. Read which rows turn red, then put it back.

``` code
curl -X POST http://localhost:8080/refund-eligibility-checks -H "Content-Type: application/json" \
     -d '{"orderId":"KW-1001","reason":"CHANGED_MIND","tagsAttached":false}'
```

## Troubleshooting

| You see                                                            | Cause                                              | Fix                                                                 |
|--------------------------------------------------------------------|----------------------------------------------------|---------------------------------------------------------------------|
| `UnnecessaryStubbingException`                                     | Mockito strict stubs: a stub the code never used.  | Remove the stub, or ask whether the code should have used it.       |
| A date test passes today and fails tomorrow                        | Something calls `LocalDate.now()` directly.        | Take the date from the `Clock` bean, and fix the clock in the test. |
| A row in `@CsvSource` gets `null` where you wanted an empty string | `nullValues = "-"` and `''` mean different things. | Use `''` for empty and `-` for null.                                |

## Project layout

``` tree
stations/032-return-and-refund-eligibility/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/kartwala/refunds/
│   ├── RefundController.java   ├── RefundService.java   ├── RefundRules.java
│   ├── Category.java   ├── Reason.java   ├── Order.java
│   ├── OrderLookup.java   ├── DemoOrders.java
│   ├── EligibilityAudit.java   ├── LoggingAudit.java   └── RefundsApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/kartwala/refunds/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the pieces it uses.

#### `src/main/java/com/kartwala/refunds/RefundController.java`

Does  
Validates the request and returns the decision.

Why  
Only the shape is checked here; what the rules need per category is checked where the category is known.

Without it  
Business rules in the controller, where only an HTTP test can reach them.

#### `src/main/java/com/kartwala/refunds/RefundService.java`

Does  
Finds the order, works out today, asks the rules, records the decision.

Why  
The only class that knows the time, and the one place with side effects.

Without it  
`LocalDate.now()` inside the rules: a test then depends on the day it runs.

#### `src/main/java/com/kartwala/refunds/RefundRules.java`

Does  
Every rule, as one pure function that returns all the reasons.

Why  
No Spring and no clock: a test passes everything in and gets a value back.

Without it  
Stopping at the first reason, so the customer fixes one thing and is refused again.

#### `src/main/java/com/kartwala/refunds/Category.java`

Does  
Each category's window and accepted reasons.

Why  
Data per category: changing electronics cannot touch clothing.

Without it  
The trap: a switch with shared cases.

#### `src/main/java/com/kartwala/refunds/Reason.java`

The five reasons, and which are the customer's choice.

#### `src/main/java/com/kartwala/refunds/Order.java`

One order with one item.

#### `src/main/java/com/kartwala/refunds/OrderLookup.java`

Where orders come from: a query.

#### `src/main/java/com/kartwala/refunds/DemoOrders.java`

Six demo orders, delivered a fixed number of days before startup.

#### `src/main/java/com/kartwala/refunds/EligibilityAudit.java`

Records each decision: a command.

#### `src/main/java/com/kartwala/refunds/LoggingAudit.java`

The demo audit: one log line per decision.

#### `src/main/java/com/kartwala/refunds/RefundsApplication.java`

Entry point, and the `Clock` bean tests replace.

#### `src/main/resources/application.yaml`

Problem details, and unknown JSON fields refused.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                              | Test class                  | Result |
|---------------|------------------------------------------|-----------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found | `RefundContractTest` (4)    | pass   |
| Every station | Reproduce the failure before the fix     | `HappyPathOnlyTrapTest` (3) | pass   |
| This station  | Every rule as a table                    | `RefundRulesTest` (28 runs) | pass   |
| This station  | Stub vs verify; India's date             | `RefundServiceTest` (3)     | pass   |

A parameterized test counts once per row: `RefundRulesTest` has five test methods.

## Stub the question, verify the command

| Collaborator              | Kind                                     | In the test                 | Why                                                                                                                          |
|---------------------------|------------------------------------------|-----------------------------|------------------------------------------------------------------------------------------------------------------------------|
| `OrderLookup.find`        | Query: returns data, changes nothing     | `when(...).thenReturn(...)` | What it returns shapes the result. How often it is called is a detail; verifying it makes tests break on harmless refactors. |
| `EligibilityAudit.record` | Command: does something, returns nothing | `verify(audit).record(...)` | Its effect is the behaviour. Nothing else would notice if it stopped being called.                                           |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.refunds.HappyPathOnlyTrapTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.refunds.RefundContractTest
[INFO] Tests run: 28, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.refunds.RefundRulesTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.refunds.RefundServiceTest
[INFO] Tests run: 38, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/kartwala/refunds/RefundRulesTest.java`

The rule table, the last day of every category, hygiene items, the fee, and undelivered orders.

#### `src/test/java/com/kartwala/refunds/RefundServiceTest.java`

Mockito with strict stubs, a fixed clock at 01:30 in India, and the audit verified.

#### `src/test/java/com/kartwala/refunds/RefundContractTest.java`

HTTP, with the app's `Clock` replaced by a fixed one.

#### `src/test/java/com/kartwala/refunds/HappyPathOnlyTrapTest.java`

Written first: the old suite's only test, and what it missed.

#### `src/test/java/com/kartwala/refunds/OldRefundRules.java`

The old window rule, kept only in tests.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/kartwala/refunds/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=FootwearChallengeTest`.
3.  Change the code until it passes, then run `./mvnw test`: the rule table must stay green.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 57 tests pass. That count is higher than the station's 38 plus the challenge tests alone, because `@EnumSource` runs once more for the new category.

Challenge 1 · Beginner-friendly · about 25 minutes

## Footwear, without breaking clothing

Add a `FOOTWEAR` category: 15 days, every reason except not-as-described, and like clothing, tags attached for a customer's-choice return. The tags question becomes required for footwear.

**Done when:** both tests in `FootwearChallengeTest` pass, and `RefundRulesTest` stays green.

Hints

- Which rule is "clothing" and which is "needs tags"? Hygiene stays clothing-only.
- A small method on `Category` says which categories need tags; the rules and the service both ask it.

#### `challenge/FootwearChallengeTest.java`

``` code
package com.kartwala.refunds;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.springframework.web.ErrorResponseException;

import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * Challenge 1: Kartwala starts selling shoes. Add a FOOTWEAR category: 15 days, accepts every reason except
 * NOT_AS_DESCRIBED, and like clothing, a customer's-choice return needs the tags attached. Nothing else may change:
 * the station's own table must stay green.
 */
class FootwearChallengeTest {

    static final LocalDate TODAY = LocalDate.of(2026, 10, 15);

    @ParameterizedTest(name = "footwear delivered {0} days ago, {1}, tags {2} -> {3}")
    @CsvSource(textBlock = """
            15, SIZE_ISSUE,       true,  ''
            16, DAMAGED,          true,  WINDOW_CLOSED
            4,  CHANGED_MIND,     false, TAGS_REMOVED
            4,  WRONG_ITEM,       false, ''
            4,  NOT_AS_DESCRIBED, true,  REASON_NOT_ACCEPTED
            """)
    void footwearRules(int daysAgo, Reason reason, boolean tags, String refused) {
        Order shoes = new Order("KW-2001", "Running shoes", Category.valueOf("FOOTWEAR"), 299_900, TODAY.minusDays(daysAgo), false);
        List<String> expected = refused.isEmpty() ? List.of() : Arrays.asList(refused.split("\\|"));
        assertThat(RefundRules.check(shoes, reason, tags, null, TODAY).reasons()).containsExactlyElementsOf(expected);
    }

    @Test
    void theTagsQuestionIsRequiredForFootwear() {
        OrderLookup orders = mock(OrderLookup.class);
        when(orders.find("KW-2001")).thenReturn(Optional.of(
                new Order("KW-2001", "Running shoes", Category.valueOf("FOOTWEAR"), 299_900, TODAY, false)));
        RefundService service = new RefundService(orders, mock(EligibilityAudit.class), Clock.fixed(Instant.parse("2026-10-15T06:00:00Z"), ZoneOffset.UTC));
        assertThatThrownBy(() -> service.check("KW-2001", Reason.SIZE_ISSUE, null, null))
                .isInstanceOfSatisfying(ErrorResponseException.class, e -> assertThat(e.getBody().getDetail()).isEqualTo("tagsAttached is required for footwear."));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## A festive-season extension

Clothing and books delivered from 15 October to 15 November 2026 can be returned until 30 November, or until their normal last day if that is later. Other categories are unchanged.

**Done when:** all twelve runs of `FestiveExtensionChallengeTest` pass.

Hints

- Test the day before, the first day, the last day and the day after: that is where date bugs live.
- `!d.isBefore(from) && !d.isAfter(to)` includes both ends.

#### `challenge/FestiveExtensionChallengeTest.java`

``` code
package com.kartwala.refunds;

import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import java.time.LocalDate;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 2: festive season (demo rule). Clothing and books delivered from 15 October to 15 November 2026, both days
 * included, can be returned until 30 November 2026, or until their normal last day if that is later. Other
 * categories keep their normal window. Boundaries are where date bugs live: test the day before, the first and last
 * days, and the day after.
 */
class FestiveExtensionChallengeTest {

    @ParameterizedTest(name = "{0} delivered {1} -> last day {2}")
    @CsvSource(textBlock = """
            CLOTHING,    2026-10-14, 2026-11-13
            CLOTHING,    2026-10-15, 2026-11-30
            CLOTHING,    2026-11-15, 2026-12-15
            CLOTHING,    2026-11-16, 2026-12-16
            BOOKS,       2026-10-14, 2026-10-24
            BOOKS,       2026-10-15, 2026-11-30
            BOOKS,       2026-11-15, 2026-11-30
            BOOKS,       2026-11-16, 2026-11-26
            ELECTRONICS, 2026-10-20, 2026-10-27
            GROCERY,     2026-10-20, 2026-10-22
            """)
    void lastDayToReturn(Category category, LocalDate deliveredOn, LocalDate lastDay) {
        Order order = new Order("KW-3001", "item", category, 100_000, deliveredOn, false);
        RefundRules.Decision d = RefundRules.check(order, Reason.WRONG_ITEM, true, true, deliveredOn);
        assertThat(d.lastDayToReturn()).isEqualTo(lastDay);
    }

    @ParameterizedTest(name = "a book delivered on 20 October, checked on {0} -> eligible {1}")
    @CsvSource({"2026-11-30, true", "2026-12-01, false"})
    void theExtensionIsEnforcedNotJustShown(LocalDate today, boolean eligible) {
        Order novel = new Order("KW-3002", "Novel", Category.BOOKS, 39_900, LocalDate.of(2026, 10, 20), false);
        assertThat(RefundRules.check(novel, Reason.CHANGED_MIND, null, null, today).eligible()).isEqualTo(eligible);
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Who owns the rule table?

The category team wants to change windows and reasons without a developer. Compare: rules in code (as now), rules in a database table with an admin screen, and a rules engine. For each, where do the table tests live, and what stops a change for one category from reaching another?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the old switch passes its own test and refuses clothing.
2.  Move each category's window and reasons onto the category.
3.  Pull the rules into a pure function and test it as a table.
4.  Keep time, lookups and recording in the service, and test it with Mockito and a fixed clock.

## Design alternatives and trade-offs

| Approach                             | What it costs                                   | Verdict                       |
|--------------------------------------|-------------------------------------------------|-------------------------------|
| Pure rules + table tests             | Inputs passed explicitly.                       | Chosen                        |
| A switch with shared cases           | One edit can change several categories.         | The trap                      |
| Only HTTP tests                      | Seconds per case, so few cases get written.     | For the contract only         |
| A rules engine (Drools and the like) | A new language and toolchain for a dozen rules. | When rules number in hundreds |
| Verifying every mock call            | Tests break on harmless refactors.              | Brittle                       |

## Database design

None in this station. If the rules move to a table: `return_policy(category primary key, window_days check (window_days between 0 and 90))` and `return_policy_reason(category, reason, primary key (category, reason))`, so a category cannot have two windows.

# 3 · Go deeper: Production

Time zones  
Servers usually run in UTC. Windows promised to customers are in their calendar; a refusal at 1 a.m. that should have been an approval is a support ticket.

Audit  
Recording every decision with its reasons answers "why was I refused?" weeks later, and shows which rule refuses most.

Consumer law  
Real return policies must respect consumer protection rules (in India, the Consumer Protection (E-Commerce) Rules, 2020); the windows here are demo values.

Test speed  
The rule table runs in milliseconds, so it runs on every build. Slow tests get skipped; fast tests get run.

# 3 · Go deeper: Interview

## Interview takeaways

What is a parameterized test, and when do you use one?

One test method run for each row of inputs and expected outputs (@CsvSource, @MethodSource, @EnumSource). Use it when the same rule must hold across many cases, such as every category.

Stub or verify?

Stub queries: you care what they return. Verify commands: you care that they happened. Verifying queries couples the test to how the code works, not what it does.

How do you test code that depends on the current time?

Inject a java.time.Clock and call LocalDate.now(clock). In tests use Clock.fixed. Never call LocalDate.now() with no argument in logic.

What makes code testable?

Separating decisions (pure functions) from effects (database, clock, network). The decisions are tested with many fast cases; the effects with a few.

What does Mockito's strict stubbing catch?

A stub the code never used, often a sign the test no longer tests what it claims, or a wrong argument.

## Self-check rubric

| Area        | Meets the bar                  | Above the bar                                            |
|-------------|--------------------------------|----------------------------------------------------------|
| Correctness | All 38 tests pass.             | You made the March mistake and read which rows failed.   |
| Test design | A table with one row per rule. | Boundaries: the last day and the day after.              |
| Mocks       | Stub queries, verify commands. | You can say why a test that verifies a query is brittle. |
| Design      | Rules are a pure function.     | Time comes from a Clock, in the customer's zone.         |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any rule change:

- Which other cases share the code that changed, and is there a test for each?
- Is there a test at each boundary: the last day and the day after?
- Does anything call `now()` without a clock?
- Do the mocks verify what matters, or every call?
