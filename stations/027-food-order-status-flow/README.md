# Station 027 · Food order status flow

Foundations · 0–1 years · Core · Food delivery · Types: none

Spring Boot 4.1.1 · Java 25 · Spring MVC · enum state machine · EnumMap · ConcurrentHashMap · Optional · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Three demo orders in memory. No food is cooked or delivered, and nobody is charged: a status change only updates the record.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 11 tests.

# 1 · Understand

## The problem in real life

1.  **A tablet sends the wrong button**

    A busy kitchen taps DELIVERED instead of ACCEPTED. The customer is told their food arrived; it has not been cooked.

2.  **A cancelled order gets picked up**

    The customer cancels; the rider's app still shows the order and marks it PICKED_UP. Food is made and carried for nobody.

3.  **The fix**

    Write the allowed moves down once, as a table. Every status change is checked against it, and a move it does not allow is refused with what is allowed instead.

A status is not a field anyone may set. It moves only along the arrows you drew.

## What are we building?

`POST /orders/{id}/status-changes` moves an order to a new status if the table allows it from where it is now. `GET /orders/{id}` shows the order and its history.

## An everyday analogy

A railway signal box: a train can only go from one block to the next one the signals allow. The signalman cannot send it from Pune straight to Delhi, and a cancelled train never leaves the platform.

## How it works in 4 steps

1.  **Find the order**: no such order, `404`.
2.  **Same status again?** A double tap: return the order unchanged.
3.  **Check the table**: not an allowed move, `409` naming what is allowed.
4.  **Move**: the check and the change are one step, and the change goes into the history.

Check yourself: the kitchen taps PREPARING and the customer taps cancel at the same moment. Both are allowed from ACCEPTED. What should happen?

Exactly one wins, and the other is told the order has moved on. If both "won", the kitchen would cook a cancelled order, or the customer would pay for food they cancelled.

## What this station is not

- **No sign-in.** Anyone may ask for any move here; challenge 1 adds who may do what.
- **No refunds or payments.** Cancelling only changes the status.
- **No database.** Three demo orders in memory.

## Key terms

| Term                 | Simple meaning                                                    | Everyday example                                         | In this project                 |
|----------------------|-------------------------------------------------------------------|----------------------------------------------------------|---------------------------------|
| **Status**           | Where an order is in its life.                                    | Placed, accepted, being prepared, out for delivery.      | `OrderStatus`                   |
| **State machine**    | A fixed set of statuses and the moves allowed between them.       | A board game: you can only move along the arrows.        | `OrderStatus` and its table     |
| **Transition table** | The list of allowed moves, from each status.                      | A train timetable: which stations follow which.          | `NEXT` (an `EnumMap`)           |
| **Terminal status**  | A status with no way out.                                         | A cancelled ticket stays cancelled.                      | DELIVERED, CANCELLED, REJECTED  |
| **409 Conflict**     | "Your request is valid, but it conflicts with the current state." | Asking to board a train that has left.                   | A move the table does not allow |
| **Optional**         | A value that may be missing, said in the type.                    | An envelope that may be empty: you check before reading. | `orders.find(id)`               |

# 2 · Build: Spec

## Business problem

**Tiffino** (a fictional food delivery app) stores an order's status as whatever the last tablet or app sent. Kitchens mark orders DELIVERED before cooking them, riders pick up cancelled orders, and support cannot tell what really happened.

## Acceptance criteria

1.  **Given** a placed order, **then** it can go ACCEPTED, PREPARING, READY_FOR_PICKUP, PICKED_UP, DELIVERED, one step at a time, with each step in its history.
2.  **Given** a placed order, **when** DELIVERED is asked, **then** `409` naming ACCEPTED, REJECTED and CANCELLED as allowed.
3.  **Given** a cancelled order, **when** any move is asked, **then** `409`: nothing can change now.
4.  **Given** the current status asked again, **then** `200` and no new history entry.
5.  **Given** two allowed moves at the same instant, **then** exactly one happens.
6.  **Given** an unknown status or no status, **then** `400`; an unknown order, `404`.

## Requirements

- The table is the only rule: PLACED → ACCEPTED, REJECTED, CANCELLED; ACCEPTED → PREPARING, CANCELLED; PREPARING → READY_FOR_PICKUP; READY_FOR_PICKUP → PICKED_UP; PICKED_UP → DELIVERED.
- DELIVERED, CANCELLED and REJECTED are final.
- Status names are exact (`ACCEPTED`, not `accepted`).
- Each move is checked and applied atomically; history times come from an injected clock.

## Learning objectives

- Model a lifecycle as an enum state machine with a transition table.
- Use `409` for a valid request that conflicts with the current state.
- Use `Optional` for "may not exist" instead of `null`.
- Test a table exhaustively, and test two moves racing.

# 2 · Build: API contract

## Endpoints

| Method | Path                          | Purpose                                       |
|--------|-------------------------------|-----------------------------------------------|
| `GET`  | `/orders/{id}`                | The order, its status and its history.        |
| `POST` | `/orders/{id}/status-changes` | Move to `{"to": "…"}` if the table allows it. |

## Status codes

| Status | When                                                                                              |
|--------|---------------------------------------------------------------------------------------------------|
| 200    | The order (after the move, or unchanged for a repeat)                                             |
| 400    | No status, or a status that does not exist                                                        |
| 404    | No such order                                                                                     |
| 409    | The move is not allowed from the current status; the body names `currentStatus` and `allowedNext` |

## Captured examples

Captured with curl from the running app on 14 Oct 2026, in this order. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: a new order

**Why:** PLACED, with its history.

Request

``` code
GET /orders/1001 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 120

{
  "id": 1001,
  "restaurant": "Annapoorna Mess",
  "status": "PLACED",
  "history": [
    {
      "status": "PLACED",
      "at": "2026-10-14T13:36:17Z"
    }
  ]
}
```

### Case 2: DELIVERED straight away

**Why:** not an arrow from PLACED: `409`, naming the three moves that are.

Request

``` code
POST /orders/1001/status-changes HTTP/1.1
Content-Type: application/json

{
  "to": "DELIVERED"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Order 1001 cannot go from PLACED to DELIVERED. Allowed next: [ACCEPTED, REJECTED, CANCELLED].",
  "instance": "/orders/1001/status-changes",
  "status": 409,
  "title": "Status change not allowed",
  "currentStatus": "PLACED",
  "allowedNext": [
    "ACCEPTED",
    "REJECTED",
    "CANCELLED"
  ]
}
```

### Case 3: ACCEPTED

**Why:** allowed: the status moves and the history grows.

Request

``` code
POST /orders/1001/status-changes HTTP/1.1
Content-Type: application/json

{
  "to": "ACCEPTED"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 172

{
  "id": 1001,
  "restaurant": "Annapoorna Mess",
  "status": "ACCEPTED",
  "history": [
    {
      "status": "PLACED",
      "at": "2026-10-14T13:36:17Z"
    },
    {
      "status": "ACCEPTED",
      "at": "2026-10-14T13:36:18Z"
    }
  ]
}
```

### Case 4: ACCEPTED again

**Why:** a double tap is not a move: `200`, history unchanged.

Request

``` code
POST /orders/1001/status-changes HTTP/1.1
Content-Type: application/json

{
  "to": "ACCEPTED"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 172

{
  "id": 1001,
  "restaurant": "Annapoorna Mess",
  "status": "ACCEPTED",
  "history": [
    {
      "status": "PLACED",
      "at": "2026-10-14T13:36:17Z"
    },
    {
      "status": "ACCEPTED",
      "at": "2026-10-14T13:36:18Z"
    }
  ]
}
```

### Case 5: picking up a cancelled order

**Why:** CANCELLED is final: `409`, and nothing can change now.

Request

``` code
POST /orders/1002/status-changes HTTP/1.1
Content-Type: application/json

{
  "to": "PICKED_UP"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Order 1002 cannot go from CANCELLED to PICKED_UP. It is CANCELLED: nothing can change now.",
  "instance": "/orders/1002/status-changes",
  "status": 409,
  "title": "Status change not allowed",
  "currentStatus": "CANCELLED",
  "allowedNext": []
}
```

### Case 6: a made-up status

**Why:** not one of the statuses: `400`.

Request

``` code
POST /orders/1001/status-changes HTTP/1.1
Content-Type: application/json

{
  "to": "TELEPORTED"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Failed to read request",
  "instance": "/orders/1001/status-changes",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 7: an unknown order

**Why:** `404`.

Request

``` code
GET /orders/9999 HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No order 9999.",
  "instance": "/orders/9999",
  "status": 404,
  "title": "Order not found"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                           | What happens                                          | Proved by                                                 |
|------------------------------------------------|-------------------------------------------------------|-----------------------------------------------------------|
| PLACED to DELIVERED, one step at a time        | Each 200; 6 history entries                           | `anOrderGoesFromPlacedToDeliveredOneStepAtATime`          |
| The same status twice                          | 200, no new entry                                     | `aDoubleTapIsNotAnErrorAndNotASecondStep`                 |
| PREPARING to DELIVERED                         | `409`; status unchanged                               | `aRefusedMoveSaysWhatIsAllowed`                           |
| Order 9999                                     | `404`                                                 | `anUnknownOrderIs404`                                     |
| TELEPORTED, lower case, none, a non-numeric id | `400`                                                 | `anUnknownStatusOrNoStatusIs400`                          |
| All 64 from–to pairs                           | Match the hand-written rule                           | `everyPairOfStatusesMatchesTheRule`                       |
| Reachability                                   | Every status reachable; only the three ends are final | `everyStatusIsReachableFromPlacedAndOnlyEndsHaveNoWayOut` |
| PREPARING and CANCELLED at once, 50 rounds     | Exactly one wins each time                            | `whenTheKitchenAndTheCustomerTapAtOnceExactlyOneWins`     |

## The trap

Plausible but wrong

Setting any status the client sends, so DELIVERED can come before PREPARING.

A setter is the simplest thing that works in a demo. The first test shows the old order accepting DELIVERED before anything else; the second, a cancelled order being picked up. The third shows the real flow refusing both with `409`. While building, skipping the table check turned 3 tests red, treating a double tap as an error turned 1 red, and replacing the atomic move with get, check, put made the racing test fail in round 0 or 1 on each of 3 runs.

``` code
package com.tiffino.orders;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The first test written for this station: it reproduces the bugs before the fix. */
class AnyStatusTrapTest extends ApiTest {

    /** The "before" order: a status field the client sets to whatever it sends. Kept only in tests. */
    static final class OldOrder {
        String status = "PLACED";

        void setStatus(String to) {
            status = to;
        }
    }

    @Test
    void theOldOrderAcceptsDeliveredBeforeItWasEvenAccepted() {
        OldOrder order = new OldOrder();
        order.setStatus("DELIVERED");
        assertThat(order.status).isEqualTo("DELIVERED");   // the customer is told their food arrived
    }

    @Test
    void theOldOrderLetsACancelledOrderBePickedUp() {
        OldOrder order = new OldOrder();
        order.setStatus("CANCELLED");
        order.setStatus("PICKED_UP");
        assertThat(order.status).isEqualTo("PICKED_UP");   // a rider collects food nobody will pay for
    }

    @Test
    void theRealFlowRefusesBothWith409() throws Exception {
        change(1001, "DELIVERED").andExpect(status().isConflict())
                .andExpect(jsonPath("$.detail").value("Order 1001 cannot go from PLACED to DELIVERED. Allowed next: [ACCEPTED, REJECTED, CANCELLED]."));
        change(1002, "PICKED_UP").andExpect(status().isConflict())
                .andExpect(jsonPath("$.detail").value("Order 1002 cannot go from CANCELLED to PICKED_UP. It is CANCELLED: nothing can change now."));
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
./mvnw test                 # all 11 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Order 1003 is being prepared. Try to deliver it, then follow the arrows.

``` code
curl -i -X POST http://localhost:8080/orders/1003/status-changes -H "Content-Type: application/json" -d '{"to":"DELIVERED"}'
curl -X POST http://localhost:8080/orders/1003/status-changes -H "Content-Type: application/json" -d '{"to":"READY_FOR_PICKUP"}'
```

## Troubleshooting

| You see                                  | Cause                                             | Fix                             |
|------------------------------------------|---------------------------------------------------|---------------------------------|
| `409`                                    | The move is not an arrow from the current status. | Read `allowedNext` in the body. |
| `400` for `accepted`                     | Status names are exact.                           | Send `ACCEPTED`.                |
| Orders back to the start after a restart | Orders live in memory.                            | Expected in this station.       |

## Project layout

``` tree
stations/027-food-order-status-flow/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tiffino/orders/
│   ├── OrderController.java   ├── OrderStatus.java   ├── Orders.java   └── OrdersApplication.java
├── src/test/java/com/tiffino/orders/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/tiffino/orders/OrderController.java`

Does  
Finds the order or 404s; asks for the move; turns a refused move into a 409 with what is allowed.

Why  
The controller has no rules: it translates `Optional` and `IllegalMove` into HTTP.

Without it  
Rules in `if` statements in the controller.

#### `src/main/java/com/tiffino/orders/OrderStatus.java`

Does  
The statuses and the transition table.

Why  
One `EnumMap` is the whole rule: easy to read, easy to test exhaustively.

Without it  
The trap: no table at all.

- The table is filled in a `static` block, because an enum constant cannot refer to constants declared after it.
- Terminal statuses map to empty sets.

#### `src/main/java/com/tiffino/orders/Orders.java`

Does  
The orders, and the only method that changes a status.

Why  
`computeIfPresent`: check the table and write the new status as one step per order.

Without it  
Read, check, then write: two moves at once both pass the check.

#### `src/main/resources/application.yaml`

Problem bodies for every error.

#### `src/main/java/com/tiffino/orders/OrdersApplication.java`

Entry point, and the `Clock` for history times.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                   | Test class                    | Result |
|---------------|-----------------------------------------------|-------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found      | `OrderStatusContractTest` (5) | pass   |
| Every station | Reproduce the failure before the fix          | `AnyStatusTrapTest` (3)       | pass   |
| This station  | The table, pair by pair, and two moves racing | `TransitionTableTest` (3)     | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.orders.OrderStatusContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.orders.TransitionTableTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.tiffino.orders.AnyStatusTrapTest
[INFO] Tests run: 11, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/tiffino/orders/AnyStatusTrapTest.java`

Written first: the old setter's DELIVERED-first and picked-up-after-cancel, and the real 409s.

#### `src/test/java/com/tiffino/orders/OrderStatusContractTest.java`

The whole happy path, a double tap, a refused move, and bad requests.

#### `src/test/java/com/tiffino/orders/TransitionTableTest.java`

All 64 pairs against a rule written by hand, reachability, and two moves racing for 50 rounds.

#### `src/test/java/com/tiffino/orders/ApiTest.java`

Shared setup: fresh demo orders before each test, and a helper that sends each move as the party that would make it.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/tiffino/orders/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=WhoMayMoveChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 11 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 14 tests pass (11 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Who may make which move

Read an `X-Actor` header (RESTAURANT, RIDER or CUSTOMER; a stand-in for real sign-in). Kitchens accept, reject, prepare, mark ready and may cancel; riders pick up and deliver; customers may only cancel. The wrong party is `403`; the table still gives `409`.

**Done when:** both tests in `WhoMayMoveChallengeTest` pass, and the station's tests still pass.

Hints

- An `Actor` enum with the statuses each party may move to: data on the enum, like the table.
- A header Spring can turn into the enum: a missing or unknown one is a `400` on its own.

#### `challenge/WhoMayMoveChallengeTest.java`

``` code
package com.tiffino.orders;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: who may make which move. X-Actor stands in for real sign-in in this demo. Kitchens accept, reject,
 * prepare, mark ready and may cancel; riders pick up and deliver; customers may only cancel. A move by the wrong
 * party is 403; a move the table forbids is still 409.
 */
class WhoMayMoveChallengeTest extends ApiTest {

    ResultActions as(String actor, long id, String to) throws Exception {
        var request = post("/orders/{id}/status-changes", id).contentType(MediaType.APPLICATION_JSON).content("{\"to\":\"" + to + "\"}");
        return mvc.perform(actor == null ? request : request.header("X-Actor", actor));
    }

    @Test
    void eachPartyMakesOnlyItsOwnMoves() throws Exception {
        as("RIDER", 1001, "ACCEPTED").andExpect(status().isForbidden());
        as("CUSTOMER", 1001, "ACCEPTED").andExpect(status().isForbidden());
        as("RESTAURANT", 1001, "ACCEPTED").andExpect(status().isOk());
        as("RESTAURANT", 1003, "READY_FOR_PICKUP").andExpect(status().isOk());
        as("RESTAURANT", 1003, "PICKED_UP").andExpect(status().isForbidden());
        as("RIDER", 1003, "PICKED_UP").andExpect(status().isOk());
    }

    @Test
    void theTableStillWinsAndAnActorIsRequired() throws Exception {
        as("CUSTOMER", 1003, "CANCELLED").andExpect(status().isConflict());   // too late to cancel: it is being prepared
        as(null, 1001, "ACCEPTED").andExpect(status().isBadRequest());
        as("CHEF", 1001, "ACCEPTED").andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Undo a mistaken READY

Kitchens tap READY_FOR_PICKUP too early. Allow going back to PREPARING within 2 minutes of becoming ready; refuse it after. Keep the table as it is: this is a rule about time on top of it.

**Done when:** the test in `UndoReadyChallengeTest` passes, and the exhaustive table test still passes.

Hints

- The time of the last change is in the history.
- Compare with the injected `Clock`, so the test can move time instead of waiting.

#### `challenge/UndoReadyChallengeTest.java`

``` code
package com.tiffino.orders;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.concurrent.atomic.AtomicReference;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: kitchens tap READY_FOR_PICKUP by mistake. Allow going back to PREPARING within 2 minutes of becoming
 * ready, and refuse it (409) after that. The table is unchanged: this is a rule about time, on top of it.
 */
@Import(UndoReadyChallengeTest.MovableClock.class)
class UndoReadyChallengeTest extends ApiTest {

    @TestConfiguration
    static class MovableClock {
        static final AtomicReference<Instant> NOW = new AtomicReference<>(Instant.parse("2026-10-14T12:00:00Z"));

        @Bean
        @Primary
        Clock movableClock() {
            return new Clock() {
                public Instant instant() {
                    return NOW.get();
                }

                public ZoneId getZone() {
                    return ZoneOffset.UTC;
                }

                public Clock withZone(ZoneId zone) {
                    return this;
                }
            };
        }
    }

    void advance(Duration d) {
        MovableClock.NOW.updateAndGet(t -> t.plus(d));
    }

    @Test
    void aMistakenReadyCanBeUndoneForTwoMinutes() throws Exception {
        change(1003, "READY_FOR_PICKUP").andExpect(status().isOk());
        advance(Duration.ofSeconds(90));
        change(1003, "PREPARING").andExpect(status().isOk()).andExpect(jsonPath("$.status").value("PREPARING"));
        change(1003, "READY_FOR_PICKUP").andExpect(status().isOk());
        advance(Duration.ofMinutes(3));
        change(1003, "PREPARING").andExpect(status().isConflict());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Keeping the history

With a database, would you keep only the current status in the `orders` table, or also every change in an `order_status_changes` table? How do you stop two servers making conflicting moves: a version column, a row lock, or a check constraint? What does support need to see when a customer says "my order says delivered but I have nothing"?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the old setter's impossible orders.
2.  Write the statuses and the table; test every pair against a rule written separately.
3.  Make the move one atomic step; race two moves to prove it.
4.  Map refused moves to `409` with the allowed list; make repeats harmless.

## Design alternatives and trade-offs

| Approach                                   | What it costs                                                                 | Verdict            |
|--------------------------------------------|-------------------------------------------------------------------------------|--------------------|
| Enum and a transition table                | A table to keep up to date.                                                   | Chosen             |
| A status setter                            | Any status from anywhere.                                                     | The trap           |
| `if` chains in each endpoint               | The rule is spread out and drifts.                                            | Avoid              |
| A method per move (`accept()`, `cancel()`) | Clear names; more endpoints and code.                                         | Good for few moves |
| A state machine library                    | A dependency and its concepts; worth it with guards, actions and many states. | For bigger flows   |

## Database design

None in this station. With a database: `orders.status` with a check constraint listing the valid statuses, an `order_status_changes` table (order, from, to, at, by), and the move as one `UPDATE … WHERE id = ? AND status = ?`: if no row changed, someone else moved first.

# 3 · Go deeper: Production

Tablets and apps  
Clients retry and double tap. Repeating the current status is harmless, and a `409` names what is allowed, so the app can show the right buttons.

Concurrency  
Kitchen, rider and customer act at the same time. One atomic move per order; across servers, a conditional update in the database does the same.

Support  
The history answers "what happened when". Keep who made each move as well (challenge 1).

Change  
A new status is a new enum constant and new table rows; the exhaustive test fails until the written rule is updated too.

# 3 · Go deeper: Interview

## Interview takeaways

Why model order status as a state machine?

Because only some moves make sense. A table of allowed moves turns every impossible order (delivered before cooked) into a refused request instead of bad data.

Which status code for an illegal move?

409 Conflict: the request is well formed, but it conflicts with the order's current state. 400 is for a malformed request.

How do you stop two moves at once from both happening?

Make the check and the write one atomic step: compute on a ConcurrentHashMap in memory, or UPDATE … WHERE status = expected in a database.

Why return 200 for the same status twice?

Clients retry and double tap. The order is already in that state, so the request has its intended effect; an error would only confuse the app.

What is Optional for?

To say in the type that a value may be missing, and make the caller decide what to do (orElseThrow, map) instead of meeting a null later.

## Self-check rubric

| Area        | Meets the bar                       | Above the bar                                              |
|-------------|-------------------------------------|------------------------------------------------------------|
| Correctness | All 11 tests pass.                  | You can draw the state diagram from the table.             |
| Modelling   | One table, terminal statuses empty. | Where a rule about time or people goes, outside the table. |
| Concurrency | Moves are atomic per order.         | The database version of the same guarantee.                |
| Explanation | 409 versus 400.                     | Why a double tap is a 200.                                 |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any status field:

- Can a client set any status directly?
- Is there one table of allowed moves, tested pair by pair?
- Are final statuses really final?
- Can two moves at once both succeed?
