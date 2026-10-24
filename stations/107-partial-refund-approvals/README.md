# Station 107 · Partial refund approvals

Working Systems · 0–2 years · Core · E-commerce · Types: Database, Concurrency

Spring Boot 4.1.1 · Java 25 · JdbcClient · @Transactional domain service · Spring Security (HTTP Basic) · PostgreSQL 17 · Flyway · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** No money moves: an approved refund is a record, and sending it to the payment provider is not part of this station. Orders, customers and staff are demo data.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 11 tests.

# 1 · Understand

## The problem in real life

1.  **Partial refunds**

    Kartwala's agents give partial refunds: a dent, a missing part, a late delivery. Above ₹5,000, a second person must approve.

2.  **More back than paid**

    An angry customer called again and again. Several agents refunded the same order at the same moment. Each one's screen checked "what is left" before the others had saved, and together they refunded more than the order cost.

3.  **The fix**

    The amount is reserved on the order in one step that checks and writes together, so refunds at the same moment take turns. Pending refunds count. The database refuses any total above the order, from any program.

A rule checked in one step and acted on in another is not a rule when two people act at once. Check and write together, and let the database hold the line.

## What are we building?

A refund workflow: agents ask, small refunds are approved at once, large ones wait for a different approver, and the total never passes the order.

## An everyday analogy

A shared envelope of cash for one order. Each refund is taken out of the envelope, never counted from a list; when the envelope is empty, nobody can take more, however many people reach for it at once.

## How it works in 4 steps

1.  **Reserve**: take the amount from what is left on the order, only if it fits, in one step.
2.  **Record**: up to ₹5,000, approved at once; above, waiting for a second person.
3.  **Decide**: a different approver approves, or rejects and gives the amount back.
4.  **Guard**: the database itself refuses a total above the order.

Check yourself: why do pending refunds count against the order?

Otherwise two large refunds could each wait for approval, each fitting on its own, and both be approved: more than the order again. Reserving at the request keeps the promise honest.

## What this station is not

- **No payment provider.** An approved refund is a record; sending it is another step (challenge 3).
- **No order system.** Three demo orders.
- **No real sign-in.** Four demo staff with HTTP Basic.

## Key terms

| Term                   | Simple meaning                                                                                   | Everyday example                                                               | In this project              |
|------------------------|--------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|------------------------------|
| **Partial refund**     | Giving back part of what was paid for an order.                                                  | Getting ₹500 back for a dented box.                                            | `POST /orders/{id}/refunds`  |
| **Second approver**    | A different person who must agree before a large refund goes ahead.                              | A cheque that needs two signatures.                                            | above ₹5,000                 |
| **Invariant**          | A rule that must be true at every moment, whatever happens.                                      | A bank balance never below zero.                                               | refunds ≤ the order's total  |
| **Race**               | Two requests at the same moment, each checking before the other has saved.                       | Two people booking the last seat on two screens.                               | the trap                     |
| **Conditional update** | An UPDATE that changes the row only if a condition still holds, checked and written in one step. | "Take one if any are left" said to the shopkeeper, not two separate questions. | `reserved + amount <= total` |
| **Domain service**     | One class that holds the business rules of an activity.                                          | The refunds desk's rulebook.                                                   | `Refunds`                    |

# 2 · Build: Spec

## Business problem

**Kartwala** (a fictional online store): partial refunds once added up to more than the order. Large refunds must have a second approver.

## Acceptance criteria

Demo rule: above ₹5,000 (500000 paise) needs a second person. Money in paise.

1.  **Given** an agent and an amount that fits, **then** `201`; up to ₹5,000 `APPROVED`, above `PENDING_APPROVAL`.
2.  **Given** more than is left (pending refunds included), **then** `409` with what is left.
3.  **Given** an approver who did not ask, **then** approve or reject; a rejection gives the amount back. The asker gets `403`; a second decision `409`.
4.  **Given** any number of refunds at the same moment, **then** the total never passes the order.
5.  **Given** bad input, unknown orders or refunds, or the wrong role, **then** `400`, `404`, `401`/`403`.

## Requirements

- The total rule is a named database constraint, tested with plain SQL.
- Four eyes is a named constraint too.
- A refund that cannot be recorded reserves nothing.

## Learning objectives

- Model a multi-step workflow with states and who may move between them.
- Keep an invariant over partial amounts under concurrency.
- Put the same rule in code and in the database.
- Prove it with a real concurrency test.

# 2 · Build: API contract

## Endpoints

| Method | Path                      | Who      | Purpose                                              |
|--------|---------------------------|----------|------------------------------------------------------|
| `POST` | `/orders/{id}/refunds`    | agent    | Ask for a refund: `{amountPaise, reason}`.           |
| `POST` | `/refunds/{id}/approvals` | approver | `{decision: APPROVE | REJECT}`.                      |
| `GET`  | `/orders/{id}`            | both     | Total, reserved, remaining, and the order's refunds. |

## Status codes

| Status    | When                                                       |
|-----------|------------------------------------------------------------|
| 201 / 200 | Refund recorded / decided                                  |
| 400       | Amount not positive, no reason, unknown decision           |
| 401 / 403 | Not signed in / wrong role, or deciding your own request   |
| 404       | No such order or refund                                    |
| 409       | More than is left (with `remainingPaise`); already decided |

## Captured examples

Captured with curl from the running app on 24 Oct 2026, in this order. `Date`, connection and standard security headers are left out.

### Case 1: ₹2,500 on the ₹12,500 washing machine

**Why:** up to ₹5,000: approved at once.

Request

``` code
POST /orders/5001/refunds HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "amountPaise": 250000,
  "reason": "Dent on the side panel"
}
```

Response

``` code
HTTP/1.1 201 
Location: /refunds/1
Content-Type: application/json

{
  "id": 1,
  "orderId": 5001,
  "amountPaise": 250000,
  "reason": "Dent on the side panel",
  "status": "APPROVED",
  "needsSecondApproval": false,
  "requestedBy": "asha",
  "decidedBy": "asha",
  "requestedAt": "2026-10-24T18:54:43.210549Z",
  "decidedAt": "2026-10-24T18:54:43.210549Z"
}
```

### Case 2: ₹9,000 on the same order

**Why:** above ₹5,000: waits; the amount is already reserved.

Request

``` code
POST /orders/5001/refunds HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "amountPaise": 900000,
  "reason": "Drum does not spin"
}
```

Response

``` code
HTTP/1.1 201 
Location: /refunds/2
Content-Type: application/json

{
  "id": 2,
  "orderId": 5001,
  "amountPaise": 900000,
  "reason": "Drum does not spin",
  "status": "PENDING_APPROVAL",
  "needsSecondApproval": true,
  "requestedBy": "asha",
  "decidedBy": null,
  "requestedAt": "2026-10-24T18:54:43.338775Z",
  "decidedAt": null
}
```

### Case 3: meena (agent and approver) asks for ₹6,000 on the phone

**Why:** waits for a second person.

Request

``` code
POST /orders/5003/refunds HTTP/1.1
Authorization: Basic bWVlbmE6bWVlbmEtZGVtby1wYXNz
Content-Type: application/json

{
  "amountPaise": 600000,
  "reason": "Wrong colour delivered"
}
```

Response

``` code
HTTP/1.1 201 
Location: /refunds/3
Content-Type: application/json

{
  "id": 3,
  "orderId": 5003,
  "amountPaise": 600000,
  "reason": "Wrong colour delivered",
  "status": "PENDING_APPROVAL",
  "needsSecondApproval": true,
  "requestedBy": "meena",
  "decidedBy": null,
  "requestedAt": "2026-10-24T18:54:43.436184Z",
  "decidedAt": null
}
```

### Case 4: meena approves her own request

**Why:** `403`: four eyes.

Request

``` code
POST /refunds/3/approvals HTTP/1.1
Authorization: Basic bWVlbmE6bWVlbmEtZGVtby1wYXNz
Content-Type: application/json

{
  "decision": "APPROVE"
}
```

Response

``` code
HTTP/1.1 403 
Content-Type: application/problem+json

{
  "detail": "You asked for this refund; another approver must decide it.",
  "instance": "/refunds/3/approvals",
  "status": 403,
  "title": "Forbidden"
}
```

### Case 5: raj approves case 2

**Why:** `200`, approved by raj.

Request

``` code
POST /refunds/2/approvals HTTP/1.1
Authorization: Basic cmFqOnJhai1kZW1vLXBhc3M=
Content-Type: application/json

{
  "decision": "APPROVE"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 246

{
  "id": 2,
  "orderId": 5001,
  "amountPaise": 900000,
  "reason": "Drum does not spin",
  "status": "APPROVED",
  "needsSecondApproval": true,
  "requestedBy": "asha",
  "decidedBy": "raj",
  "requestedAt": "2026-10-24T18:54:43.338775Z",
  "decidedAt": "2026-10-24T18:54:43.648260Z"
}
```

### Case 6: ₹2,000 more on the washing machine

**Why:** ₹2,500 + ₹9,000 are taken: ₹1,000 left, so `409`.

Request

``` code
POST /orders/5001/refunds HTTP/1.1
Authorization: Basic dmlrcmFtOnZpa3JhbS1kZW1vLXBhc3M=
Content-Type: application/json

{
  "amountPaise": 200000,
  "reason": "Late delivery"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Only ₹1,000.00 of this order can still be refunded.",
  "instance": "/orders/5001/refunds",
  "status": 409,
  "title": "Conflict",
  "remainingPaise": 100000
}
```

### Case 7: the washing machine order

**Why:** reserved = the two refunds.

Request

``` code
GET /orders/5001 HTTP/1.1
Authorization: Basic cmFqOnJhai1kZW1vLXBhc3M=
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 618

{
  "id": 5001,
  "customer": "Anjali Desai",
  "totalPaise": 1250000,
  "reservedPaise": 1150000,
  "remainingPaise": 100000,
  "refunds": [
    {
      "id": 1,
      "orderId": 5001,
      "amountPaise": 250000,
      "reason": "Dent on the side panel",
      "status": "APPROVED",
      "needsSecondApproval": false,
      "requestedBy": "asha",
      "decidedBy": "asha",
      "requestedAt": "2026-10-24T18:54:43.210549Z",
      "decidedAt": "2026-10-24T18:54:43.210549Z"
    },
    {
      "id": 2,
      "orderId": 5001,
      "amountPaise": 900000,
      "reason": "Drum does not spin",
      "status": "APPROVED",
      "needsSecondApproval": true,
      "requestedBy": "asha",
      "decidedBy": "raj",
      "requestedAt": "2026-10-24T18:54:43.338775Z",
      "decidedAt": "2026-10-24T18:54:43.648260Z"
    }
  ]
}
```

### Case 8: raj rejects meena's request

**Why:** rejected; the ₹6,000 goes back to the phone order.

Request

``` code
POST /refunds/3/approvals HTTP/1.1
Authorization: Basic cmFqOnJhai1kZW1vLXBhc3M=
Content-Type: application/json

{
  "decision": "REJECT"
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 251

{
  "id": 3,
  "orderId": 5003,
  "amountPaise": 600000,
  "reason": "Wrong colour delivered",
  "status": "REJECTED",
  "needsSecondApproval": true,
  "requestedBy": "meena",
  "decidedBy": "raj",
  "requestedAt": "2026-10-24T18:54:43.436184Z",
  "decidedAt": "2026-10-24T18:54:43.927559Z"
}
```

### Case 9: raj tries to approve it after all

**Why:** `409`: a decision is final.

Request

``` code
POST /refunds/3/approvals HTTP/1.1
Authorization: Basic cmFqOnJhai1kZW1vLXBhc3M=
Content-Type: application/json

{
  "decision": "APPROVE"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "This refund is already REJECTED.",
  "instance": "/refunds/3/approvals",
  "status": 409,
  "title": "Conflict"
}
```

### Case 10: no such order

**Why:** `404`.

Request

``` code
POST /orders/9999/refunds HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "amountPaise": 1000,
  "reason": "Test"
}
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "instance": "/orders/9999/refunds",
  "status": 404,
  "title": "Not Found"
}
```

### Case 11: ₹0

**Why:** `400`.

Request

``` code
POST /orders/5002/refunds HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "amountPaise": 0,
  "reason": "Test"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Invalid request content.",
  "instance": "/orders/5002/refunds",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 12: an agent approves

**Why:** `403`: not an approver.

Request

``` code
POST /refunds/1/approvals HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "decision": "APPROVE"
}
```

Response

``` code
HTTP/1.1 403 
Content-Type: application/problem+json
Content-Length: 110

{
  "title": "Not allowed",
  "status": 403,
  "detail": "This sign-in cannot do this.",
  "instance": "/refunds/1/approvals"
}
```

## Twenty at once

`docs/capture.sh` sends twenty ₹1,000 refunds for the ₹4,999 mixer at the same moment. Status codes, counted:

``` code
201: 4
409: 16
```

### Case 13: the mixer order afterwards

**Why:** four refunds, ₹4,000 reserved, ₹999 left.

Request

``` code
GET /orders/5002 HTTP/1.1
Authorization: Basic cmFqOnJhai1kZW1vLXBhc3M=
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 1123

{
  "id": 5002,
  "customer": "Rohit Bansal",
  "totalPaise": 499900,
  "reservedPaise": 400000,
  "remainingPaise": 99900,
  "refunds": [
    {
      "id": 4,
      "orderId": 5002,
      "amountPaise": 100000,
      "reason": "Customer called again",
      "status": "APPROVED",
      "needsSecondApproval": false,
      "requestedBy": "asha",
      "decidedBy": "asha",
      "requestedAt": "2026-10-24T18:54:44.562784Z",
      "decidedAt": "2026-10-24T18:54:44.562784Z"
    },
    {
      "id": 5,
      "orderId": 5002,
      "amountPaise": 100000,
      "reason": "Customer called again",
      "status": "APPROVED",
      "needsSecondApproval": false,
      "requestedBy": "asha",
      "decidedBy": "asha",
      "requestedAt": "2026-10-24T18:54:44.635705Z",
      "decidedAt": "2026-10-24T18:54:44.635705Z"
    },
    {
      "id": 6,
      "orderId": 5002,
      "amountPaise": 100000,
      "reason": "Customer called again",
      "status": "APPROVED",
      "needsSecondApproval": false,
      "requestedBy": "asha",
      "decidedBy": "asha",
      "requestedAt": "2026-10-24T18:54:44.652928Z",
      "decidedAt": "2026-10-24T18:54:44.652928Z"
    },
    {
      "id": 7,
      "orderId": 5002,
      "amountPaise": 100000,
      "reason": "Customer called again",
      "status": "APPROVED",
      "needsSecondApproval": false,
      "requestedBy": "asha",
      "decidedBy": "asha",
      "requestedAt": "2026-10-24T18:54:44.697681Z",
      "decidedAt": "2026-10-24T18:54:44.697681Z"
    }
  ]
}
```

And a hand-written UPDATE in `psql` that tries to reserve more than the order:

``` code
ERROR:  new row for relation "orders" violates check constraint "orders_refunds_within_total"
DETAIL:  Failing row contains (5002, Rohit Bansal, 499900, 600000).
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                               | What happens                                      | Proved by                                                              |
|----------------------------------------------------|---------------------------------------------------|------------------------------------------------------------------------|
| The old Java check, 20 at once                     | More than 4 refunds of ₹1,000 on ₹4,999           | `theOldJavaCheckLetsConcurrentRefundsAddUpToMoreThanTheOrder`          |
| The API, 20 at once                                | Exactly 4; 16 `409`s                              | `theApiAcceptsOnlyWhatFitsUnderTwentyAtOnce`                           |
| 40 at once, mixed amounts                          | Never past the total; reserved equals the refunds | `manyAgentsWithDifferentAmountsNeverPassTheTotal`                      |
| Two approvers at once                              | One decides; the other gets `409`                 | `twoApproversAtTheSameMomentDecideARefundOnce`                         |
| An approval and a rejection at once, 10 rounds     | One wins; the order stays consistent              | `anApprovalAndARejectionAtOnceLeaveTheOrderConsistent`                 |
| ₹5,000 and ₹5,000.01                               | Approved at once; waits                           | `upToFiveThousandRupeesIsApprovedAtOnceAboveItWaitsForASecondPerson`   |
| The asker approves; a rejection; a second decision | `403`; amount back; `409`                         | `theAskerCannotApproveARejectionGivesTheAmountBackAndADecisionIsFinal` |
| More than is left                                  | `409`, ₹ and paise left                           | `moreThanIsLeftIs409WithWhatIsLeft`                                    |
| Bad input, unknown ids, wrong roles                | `400`, `404`, `401`, `403`                        | `badInputIs400UnknownThingsAre404AndRolesAreChecked`                   |
| Plain SQL against the rules                        | Refused by named constraints                      | `theRulesAreNamedConstraintsInTheDatabase`                             |
| A refund that cannot be recorded                   | Nothing reserved                                  | `aRefundThatCannotBeRecordedReservesNothing`                           |

## The trap

Plausible but wrong

Checking the refund total only in Java, so concurrent refunds exceed the order.

- **The old way.** Add up the order's refunds, compare with the total, insert. Between the check and the insert the old code asked the payment provider whether the card could take a refund (100 ms in the test). Twenty ₹1,000 refunds at once on a ₹4,999 order: more than four pass, because each check ran before the others were saved.
- **The API.** The same twenty: exactly four, because the check and the reservation are one UPDATE on the order's row, and requests queue on it.

While building, each part was undone once: no condition in the UPDATE (the database's CHECK still refused the excess, but as a `500`) turned 3 tests red; no row lock on decisions 1; rejections that keep the amount 2; the asker allowed to approve 1; exactly ₹5,000 needing approval 1; no transaction around the request 1; decisions not final 3; agents allowed to approve 1.

``` code
package com.kartwala.refunds;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The mixer cost ₹4,999. Twenty agents, each answering a call from the same angry customer, refund ₹1,000 at the same
 * moment. Written first.
 */
class RefundOverlapTrapTest extends ApiTest {

    @Autowired
    TransactionTemplate tx;

    /**
     * The old way: add up the refunds in Java, and insert if there is room. Between the check and the insert, the old
     * code also asked the payment provider whether the card could take a refund; 100 ms stands in for that call.
     */
    boolean oldRefund(long order, long paise) {
        return Boolean.TRUE.equals(tx.execute(status -> {
            long total = jdbc.sql("SELECT total_paise FROM orders WHERE id = ?").param(order).query(Long.class).single();
            long refunded = refundedOrPending(order);
            if (refunded + paise > total) {
                return false;
            }
            jdbc.sql("SELECT pg_sleep(0.1)").query().singleValue();
            jdbc.sql("INSERT INTO refunds (order_id, amount_paise, reason, status, needs_second_approval, requested_by, decided_by, decided_at) "
                    + "VALUES (?, ?, 'Damaged on delivery', 'APPROVED', false, 'asha', 'asha', now())").params(order, paise).update();
            return true;
        }));
    }

    @Test
    void theOldJavaCheckLetsConcurrentRefundsAddUpToMoreThanTheOrder() throws Exception {
        List<Boolean> results = atOnce(20, () -> oldRefund(MIXER, 100_000));
        assertThat(results.stream().filter(b -> b).count()).as("refunds accepted").isGreaterThan(4);
        assertThat(refundedOrPending(MIXER)).as("refunded, in paise, of a ₹4,999 order").isGreaterThan(499_900);
    }

    @Test
    void theApiAcceptsOnlyWhatFitsUnderTwentyAtOnce() throws Exception {
        List<Integer> statuses = atOnce(20, () -> refund(MIXER, 100_000, "asha").andReturn().getResponse().getStatus());
        assertThat(statuses).filteredOn(s -> s == 201).hasSize(4);
        assertThat(statuses).filteredOn(s -> s == 409).hasSize(16);
        assertThat(refundedOrPending(MIXER)).isEqualTo(400_000).isEqualTo(reserved(MIXER));
    }

    /** n virtual threads, released together. */
    static <T> List<T> atOnce(int n, java.util.concurrent.Callable<T> work) throws Exception {
        CountDownLatch start = new CountDownLatch(1);
        List<Future<T>> futures = new ArrayList<>();
        try (var pool = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < n; i++) {
                futures.add(pool.submit(() -> {
                    start.await();
                    return work.call();
                }));
            }
            start.countDown();
            List<T> out = new ArrayList<>();
            for (Future<T> f : futures) {
                out.add(f.get());
            }
            return out;
        }
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                                           | Check with      |
|----------|-------------------------------------------------------------------|-----------------|
| JDK      | 25 (recommended). JDK 21 also works, see below                    | `java -version` |
| Docker   | Docker Desktop (Windows, macOS) or Docker Engine (Linux), running | `docker info`   |
| Maven    | Not needed: the project ships the Maven wrapper                   |                 |

**macOS / Linux**

``` code
docker compose up -d --wait   # PostgreSQL 17 on localhost:5432
./mvnw spring-boot:run        # the API on http://localhost:8080
./mvnw test                   # all 11 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d --wait
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Send twenty refunds at once and count the answers:

``` code
for i in $(seq 1 20); do curl -s -o /dev/null -w '%{http_code}\n' -u asha:asha-demo-pass -H 'Content-Type: application/json' \
  -d '{"amountPaise":100000,"reason":"Customer called again"}' localhost:8080/orders/5002/refunds & done | sort | uniq -c
```

Four `201`s, sixteen `409`s. Then copy the Review tab's `Refunds.java` over the real one, restart, run `docker compose down -v && docker compose up -d --wait` for a fresh database, and try again.

## Troubleshooting

| You see                                                 | Cause                                                          | Fix                                                                                       |
|---------------------------------------------------------|----------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| `500` with `orders_refunds_within_total` in the log     | Something wrote past the total without the conditional UPDATE. | Reserve with `... WHERE reserved_paise + :amount <= total_paise` and map 0 rows to `409`. |
| `409 already APPROVED` for an approver who clicked once | Two approvers at the same moment; the other one won.           | Expected: read the refund to see who decided.                                             |
| Refunds wait a long time under load                     | Requests queue on one hot order's row.                         | Expected for one order; different orders do not wait for each other.                      |

## Project layout

``` tree
stations/107-partial-refund-approvals/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/kartwala/refunds/
│   ├── RefundController.java   ├── Refunds.java   ├── SecurityConfig.java   ├── ProblemResponses.java   └── RefundsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__orders_and_refunds.sql, V2__demo_orders.sql
├── src/test/java/com/kartwala/refunds/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database.

#### `src/main/java/com/kartwala/refunds/RefundController.java`

Does  
The endpoints.

Why  
Validates input; one status and a plain sentence per rule; amounts in rupees in messages, paise in fields.

Without it  
A 500 for a full order; a reason nobody can read.

#### `src/main/java/com/kartwala/refunds/Refunds.java`

Does  
The domain service.

Why  
Reserve with one conditional UPDATE, then record; decide under a row lock; give the amount back on rejection.

Without it  
Two refunds that each fit, together more than the order; two approvers deciding one refund.

- The approval limit is copied onto each refund (`needs_second_approval`), so changing the limit later does not change what an old request needed.

#### `src/main/java/com/kartwala/refunds/SecurityConfig.java`

HTTP Basic, demo staff; agents ask, approvers decide.

#### `src/main/resources/db/migration/V1__orders_and_refunds.sql`

Does  
Orders and refunds.

Why  
The total and four-eyes rules as named constraints.

Without it  
Any program, script or console writing past the rules.

#### `src/main/resources/db/migration/V2__demo_orders.sql`

Three demo orders.

#### `src/main/resources/application.yaml`

The database and the approval limit.

#### `compose.yaml`

PostgreSQL 17 for running the app.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                             | Test class                                     | Result |
|---------------|---------------------------------------------------------|------------------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                | `RefundContractTest` (4)                       | pass   |
| Every station | Reproduce the failure before the fix                    | `RefundOverlapTrapTest` (2)                    | pass   |
| Database      | Rollback and constraint tests against a real database   | `RefundDatabaseTest` (2)                       | pass   |
| Concurrency   | A real concurrency test that proves the invariant holds | `RefundConcurrencyTest` (3), and the trap test | pass   |

Concurrency is real: virtual threads released together by a latch, against PostgreSQL 17 in Docker, and the totals are counted from the refunds themselves, not from the API's answers.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.refunds.RefundDatabaseTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.refunds.RefundConcurrencyTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.refunds.RefundContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.kartwala.refunds.RefundOverlapTrapTest
[INFO] Tests run: 11, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/kartwala/refunds/RefundOverlapTrapTest.java`

Written first: the Java check and the API, twenty at once.

#### `src/test/java/com/kartwala/refunds/RefundConcurrencyTest.java`

Approvers at once; mixed amounts at once.

#### `src/test/java/com/kartwala/refunds/RefundContractTest.java`

The workflow, its answers and its roles.

#### `src/test/java/com/kartwala/refunds/RefundDatabaseTest.java`

Named constraints with plain SQL; a rollback.

#### `src/test/java/com/kartwala/refunds/ApiTest.java`

Shared setup and the counts the tests trust.

#### `src/test/java/com/kartwala/refunds/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/kartwala/refunds/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=RejectionNoteChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 11 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 15 tests pass (11 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Say why

The customer is told why a refund was refused. A `REJECT` needs a `note` (1 to 200 characters), kept with the refund as `decisionNote`; an approval needs none.

**Done when:** both tests in `RejectionNoteChallengeTest` pass.

Hints

- A new migration, `V3__...sql`, adds the column: never edit V1 once it has run.
- Check "note required for REJECT" in the controller; the column may stay nullable.

#### `challenge/RejectionNoteChallengeTest.java`

``` code
package com.kartwala.refunds;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: the customer is told why a refund was refused, so a rejection needs a note. */
class RejectionNoteChallengeTest extends ApiTest {

    @Test
    void aRejectionWithoutANoteIs400AndTheNoteIsKept() throws Exception {
        long id = idOf(refund(PHONE, 1_000_000, "asha"));
        send(id, "{\"decision\":\"REJECT\"}").andExpect(status().isBadRequest());
        send(id, "{\"decision\":\"REJECT\",\"note\":\" \"}").andExpect(status().isBadRequest());
        send(id, "{\"decision\":\"REJECT\",\"note\":\"The phone was returned without its box.\"}")
                .andExpect(status().isOk()).andExpect(jsonPath("$.status").value("REJECTED"))
                .andExpect(jsonPath("$.decisionNote").value("The phone was returned without its box."));
    }

    @Test
    void anApprovalNeedsNoNote() throws Exception {
        long id = idOf(refund(PHONE, 1_000_000, "asha"));
        send(id, "{\"decision\":\"APPROVE\"}").andExpect(status().isOk()).andExpect(jsonPath("$.decisionNote").isEmpty());
    }

    private org.springframework.test.web.servlet.ResultActions send(long id, String json) throws Exception {
        return mvc.perform(post("/refunds/{id}/approvals", id).with(httpBasic("raj", "raj-demo-pass"))
                .contentType(MediaType.APPLICATION_JSON).content(json));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 40 minutes

## Two approvers for the biggest

Above ₹50,000, a refund needs two different approvers, neither of them the asker. The first approval is recorded as `firstApprovedBy` and the refund keeps waiting; the same person cannot give both; the database refuses it too (`refunds_two_different_approvers`).

**Done when:** both tests in `TwoApproversChallengeTest` pass.

Hints

- Copy the second limit onto the refund at request time, like `needs_second_approval`.
- The row lock in `decide` already keeps two approvals from overlapping.
- A CHECK can compare two columns of the same row.

#### `challenge/TwoApproversChallengeTest.java`

``` code
package com.kartwala.refunds;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: above ₹50,000, two different approvers, neither of them the person who asked. */
class TwoApproversChallengeTest extends ApiTest {

    static final long LAPTOP = 6001;   // ₹80,000

    @BeforeEach
    void aLaptopOrder() {
        jdbc.sql("DELETE FROM refunds WHERE order_id = ?").param(LAPTOP).update();
        jdbc.sql("DELETE FROM orders WHERE id = ?").param(LAPTOP).update();
        jdbc.sql("INSERT INTO orders (id, customer, total_paise) VALUES (?, 'Kavya Iyer', 8000000)").param(LAPTOP).update();
    }

    @Test
    void theFirstApprovalWaitsForASecondAndTheSamePersonCannotGiveBoth() throws Exception {
        long id = idOf(refund(LAPTOP, 6_000_000, "asha"));
        decide(id, "APPROVE", "raj").andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("PENDING_APPROVAL")).andExpect(jsonPath("$.firstApprovedBy").value("raj"));
        decide(id, "APPROVE", "raj").andExpect(status().isForbidden());
        decide(id, "APPROVE", "meena").andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("APPROVED")).andExpect(jsonPath("$.decidedBy").value("meena"));
    }

    @Test
    void theDatabaseRefusesOnePersonTwice() {
        org.assertj.core.api.Assertions.assertThatThrownBy(() -> jdbc.sql(
                        "INSERT INTO refunds (order_id, amount_paise, reason, status, needs_second_approval, requested_by, first_approved_by, decided_by) "
                                + "VALUES (?, 6000000, 'test', 'APPROVED', true, 'asha', 'raj', 'raj')").param(LAPTOP).update())
                .hasMessageContaining("refunds_two_different_approvers");
        assertThat(reserved(LAPTOP)).isZero();
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Refunds that really move money

Approved refunds must now go to the payment provider. Design the step: when it is called (inside the approval's transaction or after it), what happens when the provider times out, how a retry avoids paying twice (its idempotency key), and what the order shows while a refund is "approved but not yet paid".

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the Java check, twenty at once.
2.  Keep a running reserved amount on the order, guarded by a CHECK.
3.  Reserve with a conditional UPDATE; 0 rows means `409`.
4.  Decisions under a row lock; rejections release; four eyes in code and in the database.

## Design alternatives and trade-offs

| Approach                                                  | What it costs                                        | Verdict           |
|-----------------------------------------------------------|------------------------------------------------------|-------------------|
| Reserved amount on the order + conditional UPDATE + CHECK | One column kept in step with the refunds.            | Chosen            |
| Sum in Java, then insert                                  | Correct alone; wrong at the same moment.             | The trap          |
| `SELECT ... FOR UPDATE` on the order, then sum            | Also correct; two statements and a lock to remember. | Fine too          |
| SERIALIZABLE isolation                                    | Correct; callers must retry serialization failures.  | Fine with retries |
| A trigger that sums refunds                               | Rule in the database only; harder to read and test.  | Possible          |

## Database design

| Constraint                                  | Rule                                                  | Why                                              |
|---------------------------------------------|-------------------------------------------------------|--------------------------------------------------|
| `orders_refunds_within_total`               | 0 ≤ reserved ≤ total                                  | The invariant, for any writer.                   |
| `refunds_second_person`                     | the decider is not the asker, when approval is needed | Four eyes.                                       |
| `refunds_decided_by_someone`                | a decided refund has a decider                        | Nothing approved by nobody.                      |
| `refunds_small_not_pending`                 | a refund that needs no approval is approved           | No refunds stuck waiting for nothing.            |
| `refunds_amount_positive`, `refunds_status` | amount \> 0; known states                             | No zero or negative refunds; no invented states. |

**Transaction boundaries:** a request reserves and records in one transaction (a failed insert releases the reservation); a decision locks the refund, updates it and, on rejection, the order, in one transaction.

``` code
-- Orders and their refunds. All money in paise.
CREATE TABLE orders (
    id             BIGINT PRIMARY KEY,
    customer       TEXT   NOT NULL,
    total_paise    BIGINT NOT NULL CONSTRAINT orders_total_positive CHECK (total_paise > 0),
    -- Approved refunds plus those waiting for approval: what may no longer be refunded.
    reserved_paise BIGINT NOT NULL DEFAULT 0,
    -- The rule itself, for every writer: never more refunded (or promised) than was paid.
    CONSTRAINT orders_refunds_within_total CHECK (reserved_paise BETWEEN 0 AND total_paise)
);

CREATE TABLE refunds (
    id           BIGSERIAL PRIMARY KEY,
    order_id     BIGINT      NOT NULL REFERENCES orders (id),
    amount_paise BIGINT      NOT NULL CONSTRAINT refunds_amount_positive CHECK (amount_paise > 0),
    reason       VARCHAR(200) NOT NULL,
    status       TEXT        NOT NULL CONSTRAINT refunds_status CHECK (status IN ('PENDING_APPROVAL', 'APPROVED', 'REJECTED')),
    -- Above the limit, the amount at the time of the request: kept with the row so a later change of the limit
    -- does not change what this refund needed.
    needs_second_approval BOOLEAN NOT NULL,
    requested_by TEXT        NOT NULL,
    decided_by   TEXT,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at   TIMESTAMPTZ,
    -- Four eyes: whoever decides a refund that needs approval is not the person who asked for it.
    CONSTRAINT refunds_second_person CHECK (NOT needs_second_approval OR decided_by IS NULL OR decided_by <> requested_by),
    -- A refund that needs approval is APPROVED or REJECTED only with a decider; one that does not is approved at once.
    CONSTRAINT refunds_decided_by_someone CHECK (status = 'PENDING_APPROVAL' OR decided_by IS NOT NULL),
    CONSTRAINT refunds_small_not_pending CHECK (needs_second_approval OR status = 'APPROVED')
);
CREATE INDEX refunds_by_order ON refunds (order_id);
```

# 3 · Go deeper: Production

## Real-world considerations

Audit  
Who asked, who decided, when, and the reason: kept with each refund. For disputes, this is the record.

Hot orders  
Requests for one order queue on its row: fine for refunds, which are rare per order. A design that makes thousands of writes to one row needs another shape.

The limit in rupees  
Change it in configuration; old requests keep what they needed, because the need is copied onto each refund.

Pending for ever  
A refund nobody decides blocks part of the order. Alert on pending refunds older than a day; expire them after a policy period.

# 3 · Go deeper: Interview

## Interview takeaways

Why does a sum-then-insert check fail under concurrency?

Each transaction checks before the others commit; at READ COMMITTED all see the old sum and all insert.

How do you make it safe?

Check and write in one statement (a conditional UPDATE), or lock the parent row first, and back it with a database constraint.

Why keep the rule in the database too?

Every writer obeys it: a script, a batch job, a second service, a future teammate.

How do you test it?

Many threads released together against a real database, then count the stored rows, not the HTTP answers.

What is four eyes, and where do you enforce it?

A different person must approve; in the service, and as a constraint so no path can skip it.

What is a domain service?

A class that holds one activity's rules and transactions, so controllers stay thin and the rules live in one place.

## Self-check rubric

| Area        | Meets the bar      | Above the bar                                                                          |
|-------------|--------------------|----------------------------------------------------------------------------------------|
| Correctness | All 11 tests pass. | You ran the flawed version and explained each failure.                                 |
| Invariant   | Checked in code.   | Checked in one statement and held by a named constraint, proven by a concurrency test. |
| Workflow    | States work.       | Every move has a role, a rule and a test, including the races.                         |
| Money       | Paise.             | Paise in data, rupees in messages, no doubles anywhere.                                |

# 3 · Go deeper: Review

## The pull request

A teammate "simplifies" the request: "why keep a running total when the refunds are right there? Add them up and compare." Read the file and list every problem before opening the findings.

#### `review/Refunds.java`

``` code
package com.kartwala.refunds;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

/** The refund rules in one place. */
@Service
class Refunds {

    enum Status { PENDING_APPROVAL, APPROVED, REJECTED }

    record Refund(long id, long orderId, long amountPaise, String reason, Status status, boolean needsSecondApproval,
                  String requestedBy, String decidedBy, Instant requestedAt, Instant decidedAt) {
    }

    record Order(long id, String customer, long totalPaise, long reservedPaise, long remainingPaise, List<Refund> refunds) {
    }

    static final class NoSuchOrder extends RuntimeException {
    }

    static final class NoSuchRefund extends RuntimeException {
    }

    /** More than what is left of the order. */
    static final class NotEnoughLeft extends RuntimeException {
        final long remainingPaise;

        NotEnoughLeft(long remainingPaise) {
            this.remainingPaise = remainingPaise;
        }
    }

    static final class AlreadyDecided extends RuntimeException {
        final Status status;

        AlreadyDecided(Status status) {
            this.status = status;
        }
    }

    /** The person who asked for a refund cannot be the one who approves it. */
    static final class OwnRequest extends RuntimeException {
    }

    private static final String COLUMNS = "id, order_id, amount_paise, reason, status, needs_second_approval, requested_by, decided_by, requested_at, decided_at";
    private final JdbcClient jdbc;
    private final long approvalAbovePaise;

    Refunds(JdbcClient jdbc, @Value("${kartwala.refunds.approval-above-paise}") long approvalAbovePaise) {
        this.jdbc = jdbc;
        this.approvalAbovePaise = approvalAbovePaise;
    }

    /** Checks what is left, then records the refund: approved at once, or waiting for a second person. */
    @Transactional
    Refund request(long orderId, long amountPaise, String reason, String by) {
        // The refunds are the truth: add them up and compare with the order. No running total to keep in step.
        long total = jdbc.sql("SELECT total_paise FROM orders WHERE id = ?").param(orderId).query(Long.class).optional()
                .orElseThrow(NoSuchOrder::new);
        long taken = jdbc.sql("SELECT COALESCE(SUM(amount_paise), 0) FROM refunds WHERE order_id = ? AND status <> 'REJECTED'")
                .param(orderId).query(Long.class).single();
        if (taken + amountPaise > total) {
            throw new NotEnoughLeft(total - taken);
        }
        boolean needsApproval = amountPaise > approvalAbovePaise;
        long id = jdbc.sql("""
                        INSERT INTO refunds (order_id, amount_paise, reason, status, needs_second_approval, requested_by, decided_by, decided_at)
                        VALUES (:order, :amount, :reason, :status, :needs, :by, :decider, CASE WHEN :needs THEN NULL ELSE now() END)
                        RETURNING id""")
                .param("order", orderId).param("amount", amountPaise).param("reason", reason)
                .param("status", (needsApproval ? Status.PENDING_APPROVAL : Status.APPROVED).name()).param("needs", needsApproval)
                .param("by", by).param("decider", needsApproval ? null : by).query(Long.class).single();
        return find(id).orElseThrow();
    }

    /**
     * Approves or rejects a waiting refund. The row is locked first, so two approvers at the same moment cannot both
     * decide it; a rejected refund no longer counts in the sum.
     */
    @Transactional
    Refund decide(long refundId, boolean approve, String by) {
        Refund r = jdbc.sql("SELECT " + COLUMNS + " FROM refunds WHERE id = ? FOR UPDATE").param(refundId).query(Refund.class).optional()
                .orElseThrow(NoSuchRefund::new);
        if (r.status() != Status.PENDING_APPROVAL) {
            throw new AlreadyDecided(r.status());
        }
        if (r.requestedBy().equals(by)) {
            throw new OwnRequest();
        }
        jdbc.sql("UPDATE refunds SET status = ?, decided_by = ?, decided_at = now() WHERE id = ?")
                .params((approve ? Status.APPROVED : Status.REJECTED).name(), by, refundId).update();
        return find(refundId).orElseThrow();
    }

    Optional<Order> order(long id) {
        return jdbc.sql("SELECT id, customer, total_paise, reserved_paise FROM orders WHERE id = ?").param(id)
                .query((rs, n) -> new Order(rs.getLong("id"), rs.getString("customer"), rs.getLong("total_paise"), rs.getLong("reserved_paise"),
                        rs.getLong("total_paise") - rs.getLong("reserved_paise"),
                        jdbc.sql("SELECT " + COLUMNS + " FROM refunds WHERE order_id = ? ORDER BY id").param(id).query(Refund.class).list()))
                .optional();
    }

    private Optional<Refund> find(long id) {
        return jdbc.sql("SELECT " + COLUMNS + " FROM refunds WHERE id = ?").param(id).query(Refund.class).optional();
    }
}
```

## Findings

1The total checked in Java

"One query fewer, the same rule": the sum and the insert are two steps. Each request sees the total before the others are saved; at the same moment they all fit, and together they pass the order. And the reserved amount is no longer kept, so pending refunds stop counting too.

**Test evidence:** `theApiAcceptsOnlyWhatFitsUnderTwentyAtOnce` and `manyAgentsWithDifferentAmountsNeverPassTheTotal` fail: more refunded than the order; `anApprovalAndARejectionAtOnceLeaveTheOrderConsistent` and `upToFiveThousandRupeesIsApprovedAtOnceAboveItWaitsForASecondPerson` fail: the order's reserved amount is no longer kept, so the database's guard has nothing to guard.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class              | Fixed version | Flawed version |
|-------------------------|---------------|----------------|
| `RefundDatabaseTest`    | 2 / 2         | 2 / 2          |
| `RefundConcurrencyTest` | 3 / 3         | 1 / 3          |
| `RefundContractTest`    | 4 / 4         | 3 / 4          |
| `RefundOverlapTrapTest` | 2 / 2         | 1 / 2          |

One agent at a time, the flawed version is right. It fails on the day one customer calls five times.
