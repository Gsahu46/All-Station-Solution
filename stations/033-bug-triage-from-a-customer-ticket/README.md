# Station 033 · Bug triage from a customer ticket

Foundations · 0–1 years · Core · E-commerce · Types: Operations

Spring Boot 4.1.1 · Java 25 · stack traces · MDC request ids · @RestControllerAdvice · ProblemDetail · Micrometer · Actuator · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Orders and amounts are demo data, not Kartwala's. A refund creates a record in memory; no payment provider is called and no money moves. The ledger failure in the drill is switched on by a setting.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 15 tests.

# 1 · Understand

## The problem in real life

1.  **A ticket arrives**

    "I press refund and nothing happens." Support attaches a screenshot from the app's error log: a request id and a stack trace.

2.  **Last time, a quick patch**

    A similar ticket last month was closed with a null check where that request came in. The ticket closed; the bug moved to the cancel-whole-order path.

3.  **This time, the cause**

    Reproduce the request in a failing test, read the trace to the line that failed, ask why the value was null, and fix it where it is created, so every path is safe.

Fix the reason, not the place it showed up, and keep the test that proved it.

## What are we building?

`POST /refunds` records a refund for some lines of an order, or for every line not yet refunded. When something unexpected fails, the customer gets a message with a request id, and that id leads support straight to the stack trace.

## An everyday analogy

A doctor with a patient who has a fever. Paracetamol makes the fever go away today (the patch). A blood test finds the infection, and the right medicine stops it coming back (the cause).

## How it works in 4 steps

1.  **Read the ticket**: the request id and the error.
2.  **Find the logs** for that id, and the stack trace.
3.  **Reproduce** the request in a test that fails.
4.  **Fix the cause** until the test passes, and keep the test.

Check yourself: the patch made the ticket's request work. Why was that not enough?

It guarded one entrance to the code. The calculator underneath still assumed every order had a coupon, so the next caller (the whole-order path) failed the same way.

## What this station is not

- **No money moves.** A refund record is created in memory.
- **No log platform.** Logs go to the console; searching them by id works the same in any tool.
- **No front-end.** The app's "does nothing" was it ignoring a 500; the API now explains itself.

## Key terms

| Term                   | Simple meaning                                                                               | Everyday example                                    | In this project           |
|------------------------|----------------------------------------------------------------------------------------------|-----------------------------------------------------|---------------------------|
| **Stack trace**        | The list of method calls that were running when an error happened, newest first.             | Footprints back from where someone fell.            | `at …couponShare(…)`      |
| **Request id**         | A label on one request, shown to the customer and written on every log line of that request. | A token number at a bank counter.                   | `X-Request-Id`            |
| **Symptom**            | What the customer sees.                                                                      | A fever.                                            | "The button does nothing" |
| **Root cause**         | The mistake that produces the symptom.                                                       | The infection behind the fever.                     | a null coupon             |
| **Failing test first** | A test that reproduces the bug before you change any code.                                   | Showing the leak with water before fixing the pipe. | `NullCouponTrapTest`      |
| **Null object**        | A real object that means "nothing", used instead of `null`.                                  | A blank form instead of no form.                    | `Coupon.NONE`             |

# 2 · Build: Spec

## Business problem

**Kartwala** (a fictional shopping app) gets a ticket: the refund button does nothing for order KW-1042. The only clue is a stack trace with a request id.

## The ticket's stack trace

Real output: the ticket's request replayed on the old code (kept in the tests as `OldRefundCalculator`), this app's frames only. Produced by `docs/capture.sh`, saved in `docs/captures/ticket-stack-trace.txt`.

``` code
java.lang.NullPointerException: Cannot invoke "com.kartwala.refunds.Coupon.discountPaise()" because the return value of "com.kartwala.refunds.OldOrder.coupon()" is null
    at com.kartwala.refunds.OldRefundCalculator.couponShare(OldRefundCalculator.java:17)
    at com.kartwala.refunds.OldRefundCalculator.refundable(OldRefundCalculator.java:13)
    at com.kartwala.refunds.TicketReplay.main(TicketReplay.java:14)
```

## Reading it

1.  **The first line** is the exception and its message. Since Java 15 (by default), a `NullPointerException` says what was null: the return value of `coupon()`.
2.  **The first `at` line** is where it failed: `couponShare`. The lines below are who called it.
3.  In a full log, frames from Spring and Tomcat sit around these. Look for the first frame in your own package.
4.  Ask *why* it was null: an order without a coupon had `null` for its coupon. That is the cause.

## Acceptance criteria

1.  **Given** the ticket's request (KW-1042, line L2, no coupon), **then** `201`, ₹599.00 recorded.
2.  **Given** a whole-order refund of KW-1042, **then** `201`, ₹2,598.00: the other path works too.
3.  **Given** KW-1041 (₹200 coupon) refunded line by line, **then** the amounts add up to exactly what was paid, ₹1,598.00.
4.  **Given** a line already refunded, `409`; a line the order does not have, `422`; an unknown order, `404`.
5.  **Given** an unexpected failure, **then** `500` with the request id in the body and header, and one ERROR log line with that id and the stack trace.

## Requirements

- A failing test that reproduces the ticket comes before the fix, and stays.
- Fix where the bad value is created, so every caller is safe.
- Coupon share is proportional to price; the refund that empties the order gets what is left.
- Money in integer paise; ids normalised with `Locale.ROOT`.

## Learning objectives

- Read a stack trace: message, first frame, your own frames, the cause.
- Find every log line of one request by its id.
- Reproduce a bug with a failing test before fixing it.
- Tell a fix of the cause from a patch of the symptom.

# 2 · Build: API contract

## Endpoint

| Method | Path       | Body                                                                       |
|--------|------------|----------------------------------------------------------------------------|
| `POST` | `/refunds` | `{"orderId", "lineIds"?}`. Without `lineIds`, every line not yet refunded. |

## Status codes

| Status | When                                                       |
|--------|------------------------------------------------------------|
| 201    | A refund record was created                                |
| 400    | Not JSON, a bad order or line id, or an unknown field      |
| 404    | No such order                                              |
| 409    | The line, or the whole order, is already refunded          |
| 422    | A line the order does not have                             |
| 500    | Something unexpected; the body has the request id to quote |

## Captured examples

Captured with curl from the running app on 15 Oct 2026, in this order, against one app. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: the ticket's request

**Why:** no coupon is now `Coupon.NONE`: the belt's full ₹599.00.

Request

``` code
POST /refunds HTTP/1.1
Content-Type: application/json
X-Request-Id: req-5b1e9d42

{
  "orderId": "KW-1042",
  "lineIds": [
    "L2"
  ]
}
```

Response

``` code
HTTP/1.1 201 
X-Request-Id: req-5b1e9d42
Content-Type: application/json
Content-Length: 99

{
  "refundId": "RF-5001",
  "orderId": "KW-1042",
  "lineIds": [
    "L2"
  ],
  "amountPaise": 59900,
  "status": "RECORDED"
}
```

### Case 2: the same line again

**Why:** a line is refunded once: `409`.

Request

``` code
POST /refunds HTTP/1.1
Content-Type: application/json
X-Request-Id: req-5b1e9d43

{
  "orderId": "KW-1042",
  "lineIds": [
    "L2"
  ]
}
```

Response

``` code
HTTP/1.1 409 
X-Request-Id: req-5b1e9d43
Content-Type: application/problem+json

{
  "detail": "Line L2 of KW-1042 is already refunded.",
  "instance": "/refunds",
  "status": 409,
  "title": "Already refunded"
}
```

### Case 3: the rest of KW-1042

**Why:** the whole-order path, which last month's patch missed.

Request

``` code
POST /refunds HTTP/1.1
Content-Type: application/json

{
  "orderId": "KW-1042"
}
```

Response

``` code
HTTP/1.1 201 
X-Request-Id: 69b943fa-4133-4a8f-8959-87a4b5067a1c
Content-Type: application/json
Content-Length: 100

{
  "refundId": "RF-5002",
  "orderId": "KW-1042",
  "lineIds": [
    "L1"
  ],
  "amountPaise": 199900,
  "status": "RECORDED"
}
```

### Case 4: the dupatta from KW-1041

**Why:** ₹499 minus its share of the ₹200 coupon (₹55.50, rounded down to whole paise).

Request

``` code
POST /refunds HTTP/1.1
Content-Type: application/json

{
  "orderId": "KW-1041",
  "lineIds": [
    "L2"
  ]
}
```

Response

``` code
HTTP/1.1 201 
X-Request-Id: 2be020c0-6f5b-4846-83de-9c50be697cb2
Content-Type: application/json
Content-Length: 99

{
  "refundId": "RF-5003",
  "orderId": "KW-1041",
  "lineIds": [
    "L2"
  ],
  "amountPaise": 44350,
  "status": "RECORDED"
}
```

### Case 5: the rest of KW-1041

**Why:** the last refund gets what is left, so the two add up to the ₹1,598.00 paid.

Request

``` code
POST /refunds HTTP/1.1
Content-Type: application/json

{
  "orderId": "KW-1041"
}
```

Response

``` code
HTTP/1.1 201 
X-Request-Id: a4d6ff24-d034-4d24-b5ce-2a73510c49d8
Content-Type: application/json
Content-Length: 100

{
  "refundId": "RF-5004",
  "orderId": "KW-1041",
  "lineIds": [
    "L1"
  ],
  "amountPaise": 115450,
  "status": "RECORDED"
}
```

### Case 6: line L9

**Why:** `422`.

Request

``` code
POST /refunds HTTP/1.1
Content-Type: application/json

{
  "orderId": "KW-1041",
  "lineIds": [
    "L9"
  ]
}
```

Response

``` code
HTTP/1.1 422 
X-Request-Id: cac3af63-c0b4-440d-aa0f-3392b82f1424
Content-Type: application/problem+json

{
  "detail": "Order KW-1041 has no line L9.",
  "instance": "/refunds",
  "status": 422,
  "title": "Unknown line"
}
```

### Case 7: KW-9999

**Why:** `404`.

Request

``` code
POST /refunds HTTP/1.1
Content-Type: application/json

{
  "orderId": "KW-9999"
}
```

Response

``` code
HTTP/1.1 404 
X-Request-Id: 43b5c253-a473-4f94-b5ed-62272dee1b3d
Content-Type: application/problem+json

{
  "detail": "No order KW-9999.",
  "instance": "/refunds",
  "status": 404,
  "title": "Order not found"
}
```

### Case 8: the metric

**Why:** the count the dashboard and alert read.

Request

``` code
GET /actuator/metrics/refunds.requests?tag=outcome:recorded HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
X-Request-Id: 826f3657-02b4-4f9f-85ab-13ce6cc09b9d
Content-Disposition: inline;filename=f.txt
Content-Type: application/vnd.spring-boot.actuator.v3+json
Content-Length: 97

{
  "availableTags": [],
  "measurements": [
    {
      "statistic": "COUNT",
      "value": 4.0
    }
  ],
  "name": "refunds.requests"
}
```

## The same requests in the app's log

The running app's own console lines searched for the ids of cases 1 and 2 (`docs/captures/app-log.txt`; timestamps and process id removed). Only case 1 has a line: case 2's `409` is a client's mistake, not a failure, so it writes none.

``` code
INFO [rid:req-5b1e9d42] --- [kartwala-refunds] [nio-8080-exec-2] com.kartwala.refunds.RefundService       : Refund RF-5001 recorded for KW-1042 lines [L2] amount 59900 paise
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                               | What happens                                 | Proved by                                                     |
|----------------------------------------------------|----------------------------------------------|---------------------------------------------------------------|
| The ticket's exact request                         | `201`, ₹599.00                               | `theTicketsExactRequestIsRecorded`                            |
| Whole order, no coupon                             | `201`, ₹2,598.00                             | `theWholeOrderPathWorksWithoutACouponToo`                     |
| The same line twice in one request; part then rest | Counted once; totals equal what was paid     | `partRefundsOfACouponOrderAddUpToWhatWasPaid`                 |
| A line twice; the whole order twice                | `409`                                        | `aLineIsRefundedOnce`                                         |
| Unknown order; unknown line                        | `404`; `422`                                 | `unknownOrdersAndLinesAreRefused`                             |
| No order id; bad ids; an extra field; not JSON     | `400`                                        | `badBodiesAre400`                                             |
| The ledger fails                                   | `500` with the id, an ERROR line, the metric | `anUnexpectedErrorLeavesATrailFromTheCustomerToTheStackTrace` |
| The failure ends                                   | Refunds work; nothing half-recorded          | `afterTheFailureRefundsRecover`                               |

## The trap

Plausible but wrong

Fixing the symptom without a failing test first, so the bug returns.

The first test reproduces the ticket on the old code: the same `NullPointerException`, failing in `couponShare`. The second shows last month's patch: the ticket's path now works, and the whole-order path still throws. The third shows the fix at the cause: every path is safe. While building, each fix was undone once. Keeping the null coupon turned 7 tests red; not logging the error turned 1 red, dropping the last-refund rule 2, and leaving the request id out of the 500 body 1.

``` code
package com.kartwala.refunds;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The first test written for this ticket: it reproduces the customer's request on the old code before anything is
 * changed, then shows why last month's patch let the bug come back.
 */
class NullCouponTrapTest {

    static final Line JEANS = new Line("L1", "Denim jeans", 199_900);
    static final Line BELT = new Line("L2", "Leather belt", 59_900);

    @Test
    void theTicketsRequestThrowsOnTheOldCode() {
        OldOrder ticket = new OldOrder("KW-1042", List.of(JEANS, BELT), null);
        assertThatThrownBy(() -> OldRefundCalculator.refundable(ticket, List.of(BELT)))
                .isInstanceOf(NullPointerException.class)
                .hasMessageContaining("because the return value of \"com.kartwala.refunds.OldOrder.coupon()\" is null")
                .satisfies(e -> assertThat(e.getStackTrace()[0].getMethodName()).isEqualTo("couponShare"));
    }

    @Test
    void thePatchClosedTheTicketButTheBugCameBackOnAnotherPath() {
        OldOrder ticket = new OldOrder("KW-1042", List.of(JEANS, BELT), null);
        assertThat(OldRefundCalculator.patchedPartRefund(ticket, List.of(BELT))).isEqualTo(59_900);   // the symptom is gone
        assertThatThrownBy(() -> OldRefundCalculator.wholeOrderRefund(ticket)).isInstanceOf(NullPointerException.class);   // the cause is not
    }

    @Test
    void theFixIsInTheModelSoEveryPathIsSafe() {
        Order ticket = new Order("KW-1042", List.of(JEANS, BELT), null);
        assertThat(ticket.coupon()).isSameAs(Coupon.NONE);
        assertThat(RefundCalculator.amount(ticket, List.of(BELT), false, 0)).isEqualTo(59_900);
        assertThat(RefundCalculator.amount(ticket, List.of(JEANS, BELT), true, 0)).isEqualTo(259_800);
        assertThat(RefundCalculator.amount(ticket, List.of(JEANS), false, 0)).isEqualTo(199_900);
    }
}
```

``` code
package com.kartwala.refunds;

import java.util.List;

/** The refund code before the fix, kept only in tests. */
final class OldRefundCalculator {

    private OldRefundCalculator() {
    }

    static long refundable(OldOrder order, List<Line> lines) {
        long linesTotal = total(lines);
        return linesTotal - couponShare(order, linesTotal);
    }

    static long couponShare(OldOrder order, long linesTotal) {
        return order.coupon().discountPaise() * linesTotal / total(order.lines());   // assumes every order has a coupon
    }

    /** Last month's fix for a ticket like this one: a null check where that ticket's request came in. */
    static long patchedPartRefund(OldOrder order, List<Line> lines) {
        if (order.coupon() == null) {
            return total(lines);
        }
        return refundable(order, lines);
    }

    /** The cancel-the-whole-order path, written later. It calls the calculator directly, as it should. */
    static long wholeOrderRefund(OldOrder order) {
        return refundable(order, order.lines());
    }

    static long total(List<Line> lines) {
        return lines.stream().mapToLong(Line::pricePaise).sum();
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
./mvnw spring-boot:run                                    # the API on http://localhost:8080
./mvnw spring-boot:run -Dspring-boot.run.arguments=--kartwala.refunds.simulate-ledger-failure=true   # the failure drill
./mvnw test                                               # all 15 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd spring-boot:run "-Dspring-boot.run.arguments=--kartwala.refunds.simulate-ledger-failure=true"
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Bring the bug back: in `Order.java`, delete the line `coupon = coupon == null ? Coupon.NONE : coupon;` and run the tests. Read the first failure's stack trace the way the Spec tab does. Then put it back.

``` code
curl -i -X POST http://localhost:8080/refunds -H "Content-Type: application/json" \
     -H "X-Request-Id: my-ticket-0001" -d '{"orderId":"KW-1042","lineIds":["L2"]}'
```

Then search the app's console for `rid:my-ticket-0001`.

## Troubleshooting

| You see                                     | Cause                                                                      | Fix                                                                                             |
|---------------------------------------------|----------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| A stack trace with no line of your own code | The error came from a library, called by your code further down.           | Read down to the first frame in `com.kartwala`, and look for `Caused by:`.                      |
| An ERROR log line with `[rid:-]`            | It was logged after the request finished (outside the filter).             | Handle the exception inside the request, as `UnexpectedErrorHandler` does.                      |
| The NPE message says only `null`            | Helpful NullPointerException messages switched off, or Java older than 15. | Java 15 and later have them on by default; check for `-XX:-ShowCodeDetailsInExceptionMessages`. |

## Project layout

``` tree
stations/033-bug-triage-from-a-customer-ticket/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/kartwala/refunds/
│   ├── RequestIdFilter.java   ├── RefundController.java   ├── RefundService.java
│   ├── Order.java   ├── Coupon.java   ├── Line.java   ├── Orders.java
│   ├── RefundCalculator.java   ├── RefundLedger.java
│   ├── UnexpectedErrorHandler.java   └── RefundsApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/kartwala/refunds/   (see Tests; TicketReplay prints the ticket's trace)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the pieces it uses.

#### `src/main/java/com/kartwala/refunds/RequestIdFilter.java`

Does  
Gives each request an id, puts it in the MDC and the response header.

Why  
A filter, so it wraps everything, including errors.

Without it  
An id only on some log lines, or one a caller can fill with fake log text.

#### `src/main/java/com/kartwala/refunds/RefundController.java`

Does  
Validates the body and returns the refund record.

Why  
Ids normalised once, at the edge.

Without it  
A null check here for the coupon: that was the patch.

#### `src/main/java/com/kartwala/refunds/RefundService.java`

Does  
Checks the lines, computes the amount, records the refund.

Why  
No line ids means the rest of the order; a line twice in one request counts once.

Without it  
Refunding a line twice, or over-refunding with rounding.

#### `src/main/java/com/kartwala/refunds/Order.java`

Does  
An order and what was paid.

Why  
The fix lives here: the constructor turns a null coupon into `Coupon.NONE`, so no caller ever sees null.

Without it  
The trap: a null that every caller has to remember.

#### `src/main/java/com/kartwala/refunds/RefundCalculator.java`

Does  
How much comes back for some lines.

Why  
Proportional coupon share, rounded down; the last refund gets what is left.

Without it  
`order.coupon().discountPaise()` with a coupon that might be null.

#### `src/main/java/com/kartwala/refunds/UnexpectedErrorHandler.java`

Does  
Turns an unexpected exception into a 500 the customer can quote, and a log line support can find.

Why  
Logs while the request id is still in the MDC, once, at ERROR, with the stack trace.

Without it  
Letting it escape: the servlet container logs it after the filter has cleared the id.

#### `src/main/java/com/kartwala/refunds/RefundLedger.java`

Refund records in memory, and the switch the failure drill uses.

#### `src/main/java/com/kartwala/refunds/Coupon.java`

A coupon, and `Coupon.NONE`.

#### `src/main/java/com/kartwala/refunds/Line.java`

One line of an order.

#### `src/main/java/com/kartwala/refunds/Orders.java`

Two demo orders: one with a coupon, and the ticket's, without.

#### `src/main/java/com/kartwala/refunds/RefundsApplication.java`

Entry point.

#### `src/main/resources/application.yaml`

The request id in the log pattern, the metrics endpoint, strict JSON, and the drill switch (off).

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                  | Test class                 | Result |
|---------------|--------------------------------------------------------------|----------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                     | `RefundContractTest` (6)   | pass   |
| Every station | Reproduce the failure before the fix                         | `NullCouponTrapTest` (3)   | pass   |
| Operations    | Metric, alert, rollback, runbook; a controlled failure drill | `OperationsDrillTest` (3)  | pass   |
| This station  | Amounts without Spring                                       | `RefundCalculatorTest` (3) | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.refunds.RefundCalculatorTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.refunds.OperationsDrillTest
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.refunds.RefundContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.refunds.NullCouponTrapTest
[INFO] Tests run: 15, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/kartwala/refunds/NullCouponTrapTest.java`

Written first: the ticket on the old code, the patch that missed a path, and the fix.

#### `src/test/java/com/kartwala/refunds/RefundContractTest.java`

The ticket's request, both paths, the money, and every refusal.

#### `src/test/java/com/kartwala/refunds/OperationsDrillTest.java`

The failure drill: a 500 with the id, the ERROR line with the trace, the metric, recovery.

#### `src/test/java/com/kartwala/refunds/RefundCalculatorTest.java`

Coupon share, the last refund's remainder, and no coupon.

#### `src/test/java/com/kartwala/refunds/OldRefundCalculator.java`

The old code, with last month's patch.

#### `src/test/java/com/kartwala/refunds/TicketReplay.java`

Prints the ticket's real stack trace for this page.

#### `src/test/java/com/kartwala/refunds/ApiTest.java`

Shared setup: a fresh app per test, since refunds change the ledger.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/kartwala/refunds/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=FreeOrderTicketChallengeTest`. Read the stack trace first.
3.  Fix the cause until it passes, then run `./mvnw test` to check the other 15 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 19 tests pass (15 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## A second ticket: free samples

"Refund for my free samples fails." The log shows `java.lang.ArithmeticException: / by zero` in `RefundCalculator.amount`, for an order where every line cost ₹0. The failing test is written for you; fix the cause.

**Done when:** both tests in `FreeOrderTicketChallengeTest` pass, and nothing else turns red.

Hints

- Which number is zero, and why can it be?
- Nothing was paid, so nothing comes back: answer 0 before dividing.

#### `challenge/FreeOrderTicketChallengeTest.java`

``` code
package com.kartwala.refunds;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 1: a second ticket. "Refund for my free samples fails." The log shows
 * java.lang.ArithmeticException: / by zero at com.kartwala.refunds.RefundCalculator.amount
 * for an order where every line was free (two ₹0 sample lines, no coupon). This is the failing test, written first.
 * Fix the cause so it passes, and keep every other test green.
 */
class FreeOrderTicketChallengeTest {

    static final Order SAMPLES = new Order("KW-1077", List.of(new Line("L1", "Sample serum", 0), new Line("L2", "Sample cream", 0)), null);

    @Test
    void aPartRefundOfAFreeOrderIsZeroNotAnError() {
        assertThat(RefundCalculator.amount(SAMPLES, List.of(SAMPLES.lines().get(0)), false, 0)).isZero();
    }

    @Test
    void theWholeFreeOrderIsZeroToo() {
        assertThat(RefundCalculator.amount(SAMPLES, SAMPLES.lines(), true, 0)).isZero();
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## The request id on every refusal

Support wants the request id on every problem response (`400`, `404`, `409`, `422`), not only on `500`, so a customer who sees "already refunded" can be traced too.

**Done when:** both tests in `RequestIdOnEveryProblemChallengeTest` pass.

Hints

- `ResponseEntityExceptionHandler` builds every Spring problem response through one protected method.
- Override `createResponseEntity` and add the property when the body is a `ProblemDetail`.

#### `challenge/RequestIdOnEveryProblemChallengeTest.java`

``` code
package com.kartwala.refunds;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: support asks for the request id on every refusal, not just on 500s, so a customer who sees "already
 * refunded" can be traced too. Every problem response (400, 404, 409, 422) carries "requestId", equal to the
 * X-Request-Id header.
 */
class RequestIdOnEveryProblemChallengeTest extends ApiTest {

    @Test
    void refusalsCarryTheRequestId() throws Exception {
        refund("""
                {"orderId":"KW-9999"}""", "support-case-77").andExpect(status().isNotFound())
                .andExpect(jsonPath("$.requestId").value("support-case-77"));
        refund("""
                {"orderId":"KW-1042","lineIds":["L9"]}""", "support-case-78").andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.requestId").value("support-case-78"));
    }

    @Test
    void badBodiesCarryItToo() throws Exception {
        refund("not json", "support-case-79").andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.requestId").value("support-case-79"));
        refund("""
                {"orderId":"1042"}""", "support-case-80").andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.requestId").value("support-case-80"));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## A triage template for support

Write the one-page template support fills before a ticket reaches engineering: what the customer did, when, the request id, the order, the exact message shown. For each field, say which step of the runbook it saves. What would you add so that a ticket like this one is linked to the failing test that closed it?

# 3 · Go deeper: Design

## Implementation approach

1.  Find the request id's log lines and the stack trace.
2.  Write the failing test: the ticket's request on the code as it is.
3.  Ask why the value was null until the answer is a design choice (null meant "no coupon").
4.  Fix it there, run every test, and keep the new one.
5.  Make the next ticket easier: the 500 carries the id, and the log line has it.

## Design alternatives and trade-offs

| Fix                                           | What it costs                                                          | Verdict   |
|-----------------------------------------------|------------------------------------------------------------------------|-----------|
| `Coupon.NONE` set in the record's constructor | One line; every caller is safe.                                        | Chosen    |
| `Optional<Coupon>` accessor                   | Every caller must unwrap; also safe.                                   | Also fine |
| A null check in the calculator                | Fixes this calculator; the next reader of the coupon can forget again. | Partial   |
| A null check where the request comes in       | The ticket closes; other paths still fail.                             | The trap  |
| `catch (Exception e)` returning 0             | A silent wrong refund instead of an error.                             | Worse     |

## Database design

None in this station. With a database, the cause is often a nullable column: `coupon_id` nullable is fine if the code models it, and a `unique (order_id, line_id)` on the refund lines table makes "refunded once" hold across app instances.

# 3 · Go deeper: Production

## Operations

Metric  
`refunds.requests`, tagged `outcome` = recorded or failed. Client mistakes (4xx) are not failures and are not counted as them.

Alert  
Page the on-call engineer when `failed` is more than 2% of all refund requests for 10 minutes, or more than 0 for an hour at low traffic (thresholds are a starting point; tune them on real traffic).

Rollback  
The fix changes no stored data, so rolling back is redeploying the previous version. Refunds recorded meanwhile stay valid. If a release raises `failed`, roll back first and investigate from the request ids after.

## Runbook: "the refund button does nothing"

1.  Get the request id: from the customer's screenshot (the 500 body now shows it), or the app's error report.
2.  Search the logs for `[rid:<that id>]`. Read the ERROR line's exception, message and first frame in `com.kartwala`.
3.  Check `refunds.requests{outcome=failed}`: one customer, or everyone? Everyone after a release: roll back.
4.  One kind of order: write a failing test with that order's shape before touching code. Fix the cause; link the test to the ticket.

## Failure drill

A controlled failure drill, run before you need the runbook for real:

1.  Start a test instance with `--kartwala.refunds.simulate-ledger-failure=true`.
2.  Send a refund with `X-Request-Id: drill-req-0001`: expect `500`, and `requestId: drill-req-0001` in the body.
3.  Follow the runbook from that id alone: find the ERROR line and its stack trace, and see `outcome=failed` in `/actuator/metrics/refunds.requests`.
4.  Restart without the switch; the same refund now gives `201`, because nothing was recorded by the failed try.

The same drill runs on every build as `OperationsDrillTest` (3 tests, passing in `docs/test-run.txt`).

## Real-world considerations

Privacy  
Stack traces and log lines must not carry card numbers, addresses or phone numbers; log ids, not people.

Error trackers  
Tools such as Sentry group identical stack traces and count them; the request id links each event to its logs.

Regression tests  
A bug's test is named after what it proves, not the ticket number, and stays in the suite for good.

# 3 · Go deeper: Interview

## Interview takeaways

How do you read a Java stack trace?

Read the exception type and message first, then the first frame (where it was thrown), then down to the first frame in your own code. With a chain, the last 'Caused by:' is usually the origin.

A customer reports an error. What do you do first?

Get the request id or time, find the logs for it, read the error, and reproduce it with a failing test before changing anything.

Symptom fix vs root-cause fix?

A symptom fix makes the visible failure go away where it was seen. A root-cause fix removes the reason, so every path that could hit it is safe. The failing test proves which one you did.

Why log unexpected errors in a @RestControllerAdvice?

It runs inside the request, while the MDC still has the request id, and it can return a useful body. An exception that escapes is logged by the container after the filter cleared the id.

What is the null object pattern?

A real object standing for 'nothing' (Coupon.NONE, discount 0), so callers never need a null check.

## Self-check rubric

| Area        | Meets the bar                         | Above the bar                                          |
|-------------|---------------------------------------|--------------------------------------------------------|
| Correctness | All 15 tests pass.                    | You brought the bug back and read the trace.           |
| Triage      | From request id to the failing line.  | From the failing line to why the value was wrong.      |
| Testing     | A failing test before the fix.        | A test for the other paths the same cause could reach. |
| Operations  | The 500 shows the id; the log has it. | You ran the failure drill and followed the runbook.    |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any bug fix:

- Is there a test that fails without the fix? Did someone see it fail?
- Is the fix where the bad value is created, or where it was noticed?
- Which other paths read the same value?
- Would the next error of this kind reach a log line with a request id?
