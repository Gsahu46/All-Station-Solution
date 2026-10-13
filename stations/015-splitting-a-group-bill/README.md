# Station 015 · Splitting a group bill

Foundations · 0–1 years · Core · Fintech · Types: none

Spring Boot 4.1.1 · Java 25 · Spring MVC · integer paise · Map · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Expenses are records in the app's memory. Nobody is charged and no money moves: settle-up only suggests who should pay whom.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 15 tests.

# 1 · Understand

## The problem in real life

1.  **Asha pays ₹1,000 for dinner for three**

    The app splits it as ₹333.33 each. Three people owe ₹999.99. One paisa is gone, and Asha is the one who lost it.

2.  **After a week in Goa**

    Settling up shows 12 payments: everyone pays everyone back for every bill.

3.  **The fix**

    Split in whole paise and hand the leftover paise to someone by a fixed rule, so the parts always add up. Then net everyone's balance and pair the biggest debtor with the biggest creditor: at most one payment fewer than people.

Rounding each part on its own loses money. Decide who gets the remainder.

## What are we building?

`POST /groups/{id}/expenses` records who paid and splits it equally, by exact amounts, or by shares, always adding up to the paisa. `GET /groups/{id}/settle-up` shows each member's balance and the payments that clear them.

## An everyday analogy

A family shares 10 mangoes among 3 children: each gets 3, and the 10th goes to the youngest, because that is the family rule. Nobody cuts the mango into 3.33 pieces and throws away the crumbs.

## How it works in 4 steps

1.  **Record an expense**: who paid, how many paise, and how to split.
2.  **Split in whole paise**; the leftover paise go out one at a time by a fixed rule.
3.  **Keep the split** with the expense, so balances never divide again.
4.  **Settle up**: net balances, then the biggest debtor pays the biggest creditor, again and again.

Check yourself: why not just round ₹333.333 up to ₹333.34 for everyone?

Then three people owe ₹1,000.02: two paise more than Asha paid. Rounding every share the same way, up or down, never adds up in general. Only giving out the remainder one paisa at a time does.

## What this station is not

- **No real payments.** Settle-up only suggests transfers.
- **No login, no database.** Two groups are fixed in code.
- **Not the fewest possible payments in every case.** The rule guarantees at most one fewer payment than people; the true minimum is a much harder problem.

## Key terms

| Term                     | Simple meaning                                                                                            | Everyday example                                                    | In this project                               |
|--------------------------|-----------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------|-----------------------------------------------|
| **Remainder**            | What is left after dividing into equal whole parts.                                                       | 10 laddoos for 3 children: 3 each, 1 left over.                     | ₹1,000 ÷ 3 = 33,333 paise each, 1 paisa left. |
| **Paise**                | Whole hundredths of a rupee. Integers, no rounding.                                                       | ₹1,000 is 1,00,000 paise.                                           | Every amount in this API.                     |
| **Equal, exact, shares** | Three ways to split: the same for everyone, given amounts, or by weight (2:1:1).                          | Splitting a cab fare, a hotel bill by room, fuel by who drove more. | `splitType`                                   |
| **Largest remainder**    | Give each person their whole part, then hand out the leftover paise to whoever lost the biggest fraction. | Handing the extra laddoo to the child who was owed the most of it.  | `Splitter.shares`                             |
| **Net balance**          | What someone paid minus what they owe. Positive: others owe them.                                         | Asha paid ₹900, her share was ₹300: she is owed ₹600.               | `balancesPaise`                               |
| **Settle-up**            | The payments that bring every balance to zero.                                                            | At the end of a trip: "Ravi pays Asha ₹300".                        | `payments`                                    |

# 2 · Build: Spec

## Business problem

**SplitSaathi** (a fictional bill-splitting app) divides expenses with `double` and rounds each share. Totals drift by a paisa, so the person who paid is always slightly short, and support gets "the numbers don't add up" tickets. Settle-up replays every expense separately, so a weekend trip ends with a dozen transfers.

## Acceptance criteria

1.  **Given** ₹1,000 split equally among three, **then** the shares are 33,334, 33,333 and 33,333 paise: the first person listed takes the extra paisa.
2.  **Given** shares 2:1:1 of ₹1,000, **then** 50,000, 25,000, 25,000.
3.  **Given** exact amounts that do not add up to the total, **then** `422` saying by how much.
4.  **Given** anyone outside the group, a person listed twice, or a zero share, **then** `422`.
5.  **Given** a trip's expenses among four people, **then** settle-up needs at most 3 payments, and making them clears every balance.
6.  **Given** 1,000 random splits, **then** every one adds up exactly.

## Requirements

- All amounts are whole paise; ₹0.01 to ₹1,00,000 per expense (a demo rule). Fractions are `400`.
- Equal split: leftover paise go to the participants in the order listed.
- Shares: largest-remainder method; ties go in the order listed.
- Balances always add up to zero; settle-up refuses to run if they do not.

## Learning objectives

- Divide money and distribute the remainder so parts add up.
- Explain why `double`, and `BigDecimal` with per-share rounding, both lose paise.
- Implement equal, exact and share-based splits.
- Net balances with a `Map` and settle with a greedy algorithm, and state its guarantee.
- Test a rule on a thousand generated cases, not just three hand-picked ones.

# 2 · Build: API contract

## Endpoints

| Method | Path                     | Purpose                                                         |
|--------|--------------------------|-----------------------------------------------------------------|
| `POST` | `/groups/{id}/expenses`  | Record and split an expense. `201` with `owedPaise` per person. |
| `GET`  | `/groups/{id}/settle-up` | Balances and the suggested payments.                            |

## Request body

| Field         | Rule                                                                                               |
|---------------|----------------------------------------------------------------------------------------------------|
| `description` | Required, at most 80 characters.                                                                   |
| `paidBy`      | A member of the group.                                                                             |
| `amountPaise` | 1 to 10,000,000, whole number.                                                                     |
| `splitType`   | `EQUAL` (with `participants`), `EXACT` (with `exactPaise`), `SHARES` (with `shares`, 1–1000 each). |

## Status codes

| Status | When                                                                                                |
|--------|-----------------------------------------------------------------------------------------------------|
| 201    | Expense recorded                                                                                    |
| 200    | Settle-up                                                                                           |
| 400    | A field is missing or of the wrong type (including a fraction of a paisa)                           |
| 404    | No such group                                                                                       |
| 422    | The split cannot be applied: non-members, duplicates, zero shares, exact amounts that do not add up |

## Captured examples

Captured with curl from the running app on 13 Oct 2026, in this order. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: ₹1,000 among three

**Why:** 1,00,000 paise ÷ 3 = 33,333 with 1 left over; the first person listed, Asha, takes it. The parts add up to exactly 1,00,000.

Request

``` code
POST /groups/1/expenses HTTP/1.1
Content-Type: application/json

{
  "description": "Dinner",
  "paidBy": "asha",
  "amountPaise": 100000,
  "splitType": "EQUAL",
  "participants": [
    "asha",
    "ravi",
    "meera"
  ]
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 159

{
  "id": "8a3aecd8-ba8e-4be9-b2cd-4ee9caffac72",
  "description": "Dinner",
  "paidBy": "asha",
  "amountPaise": 100000,
  "owedPaise": {
    "asha": 33334,
    "ravi": 33333,
    "meera": 33333
  }
}
```

### Case 2: fuel by shares 2:1:1

**Why:** Kabir drove twice as much, so he owes half.

Request

``` code
POST /groups/1/expenses HTTP/1.1
Content-Type: application/json

{
  "description": "Fuel",
  "paidBy": "kabir",
  "amountPaise": 100000,
  "splitType": "SHARES",
  "shares": {
    "kabir": 2,
    "asha": 1,
    "ravi": 1
  }
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 158

{
  "id": "8121b399-a8a8-472e-9b8a-c19f109e2c1e",
  "description": "Fuel",
  "paidBy": "kabir",
  "amountPaise": 100000,
  "owedPaise": {
    "kabir": 50000,
    "asha": 25000,
    "ravi": 25000
  }
}
```

### Case 3: hotel by room

**Why:** exact amounts that add up to the total are stored as given.

Request

``` code
POST /groups/1/expenses HTTP/1.1
Content-Type: application/json

{
  "description": "Hotel",
  "paidBy": "ravi",
  "amountPaise": 1200000,
  "splitType": "EXACT",
  "exactPaise": {
    "asha": 500000,
    "ravi": 400000,
    "meera": 300000
  }
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 162

{
  "id": "022f2021-12e3-4def-abec-de838d5a676e",
  "description": "Hotel",
  "paidBy": "ravi",
  "amountPaise": 1200000,
  "owedPaise": {
    "asha": 500000,
    "ravi": 400000,
    "meera": 300000
  }
}
```

### Case 4: exact amounts that do not add up

**Why:** ₹9,000 of ₹12,000 assigned: `422`, saying how far off it is.

Request

``` code
POST /groups/1/expenses HTTP/1.1
Content-Type: application/json

{
  "description": "Hotel",
  "paidBy": "ravi",
  "amountPaise": 1200000,
  "splitType": "EXACT",
  "exactPaise": {
    "asha": 500000,
    "ravi": 400000
  }
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "The exact amounts add up to 900000 paise, not 1200000.",
  "instance": "/groups/1/expenses",
  "status": 422,
  "title": "Invalid split"
}
```

### Case 5: settle up

**Why:** each balance is paid minus owed, and together they add up to zero. Pairing the biggest debtor with the biggest creditor clears four people in at most three payments.

Request

``` code
GET /groups/1/settle-up HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 252

{
  "groupId": 1,
  "balancesPaise": {
    "asha": -458334,
    "kabir": 50000,
    "meera": -333333,
    "ravi": 741667
  },
  "payments": [
    {
      "from": "asha",
      "to": "ravi",
      "amountPaise": 458334
    },
    {
      "from": "meera",
      "to": "ravi",
      "amountPaise": 283333
    },
    {
      "from": "meera",
      "to": "kabir",
      "amountPaise": 50000
    }
  ]
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                           | What happens                                         | Proved by                                             |
|------------------------------------------------|------------------------------------------------------|-------------------------------------------------------|
| ₹1,000 ÷ 3                                     | 33,334 + 33,333 + 33,333                             | `theSplitterHandsTheLeftoverPaisaToSomeone`           |
| Shares 1:1:1 of ₹100; 1:1:2 of 101 paise       | 3,334/3,333/3,333; 25/25/51                          | `sharesUseTheLargestRemainder`                        |
| 1,000 random totals, group sizes and shares    | Always add up; equal parts differ by at most 1 paisa | `aThousandRandomSplitsAllAddUpExactly`                |
| Exact split                                    | Stored as given                                      | `anExactSplitIsStoredAsGiven`                         |
| Shares 2:1:1                                   | Half, quarter, quarter                               | `sharesSplitByWeight`                                 |
| Six trip expenses, four people                 | 3 payments; correct balances                         | `settleUpNeedsAtMostOneFewerPaymentThanPeople`        |
| Payments applied                               | Every balance becomes zero                           | `settleUpClearsEveryBalanceInAtMostNMinusOnePayments` |
| No expenses                                    | No payments                                          | `aGroupWithNoExpensesHasNothingToSettle`              |
| Exact amounts off by ₹3,000                    | `422`                                                | `exactAmountsThatDoNotAddUpAre422`                    |
| A non-member pays or takes part                | `422`                                                | `someoneOutsideTheGroupIs422`                         |
| Same person twice, zero share, no participants | `422`                                                | `badSplitsAre422`                                     |
| 0 paise, 1000.5 paise, unknown split type      | `400`                                                | `badFieldsAre400`                                     |
| Unknown group                                  | `404`                                                | `anUnknownGroupIs404`                                 |

## The trap

Plausible but wrong

Dividing with `double` or default rounding, so a paisa goes missing.

"Divide and round to two decimals" looks careful. The first test shows ₹333.33 × 3 = ₹999.99. The second shows that `BigDecimal` alone is not the fix: dividing ₹1,000 by 3 exactly throws an exception, and rounding each share still loses the paisa. The third test shows the real splitter handing the leftover paisa to the first person. Dropping that leftover paisa from the code was tried while building: 2 tests went red.

``` code
package com.splitsaathi.groups;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * The first test written for this station: it reproduces the bug before the fix.
 * Asha pays Rs 1,000 for dinner for three people.
 */
class MissingPaisaTrapTest extends ApiTest {

    /** The "before" split: divide in double, round each share to 2 decimals. Kept only in tests. */
    static double oldShare(double total, int people) {
        return Math.round(total / people * 100) / 100.0;
    }

    @Test
    void roundingEachShareSeparatelyLosesAPaisa() {
        double share = oldShare(1000.00, 3);
        assertThat(share).isEqualTo(333.33);
        assertThat(share * 3).isNotEqualTo(1000.00);   // 999.99: one paisa nobody owes, and Asha is out of pocket
    }

    @Test
    void bigDecimalDoesNotSaveYouByItself() {
        BigDecimal total = new BigDecimal("1000.00");
        // An exact division that never ends is refused...
        assertThatThrownBy(() -> total.divide(BigDecimal.valueOf(3))).isInstanceOf(ArithmeticException.class);
        // ...and rounding each share still loses the paisa. The remainder has to be handed out on purpose.
        BigDecimal share = total.divide(BigDecimal.valueOf(3), 2, RoundingMode.HALF_UP);
        assertThat(share.multiply(BigDecimal.valueOf(3))).isEqualByComparingTo("999.99");
    }

    @Test
    void theSplitterHandsTheLeftoverPaisaToSomeone() throws Exception {
        assertThat(Splitter.equal(100_000, List.of("asha", "ravi", "meera")).values()).containsExactly(33_334L, 33_333L, 33_333L);
        expense(1, """
                {"description":"Dinner","paidBy":"asha","amountPaise":100000,"splitType":"EQUAL","participants":["asha","ravi","meera"]}""")
                .andExpect(jsonPath("$.owedPaise.asha").value(33334))
                .andExpect(jsonPath("$.owedPaise.ravi").value(33333))
                .andExpect(jsonPath("$.owedPaise.meera").value(33333));
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

The body is in `docs/dinner.json` (Asha pays ₹1,000 for three).

``` code
# Split: expect owedPaise asha 33334, ravi 33333, meera 33333
curl -i -X POST http://localhost:8080/groups/1/expenses -H "Content-Type: application/json" -d "@docs/dinner.json"

# Who pays whom
curl http://localhost:8080/groups/1/settle-up
```

## Troubleshooting

| You see                            | Cause                                                       | Fix                                                      |
|------------------------------------|-------------------------------------------------------------|----------------------------------------------------------|
| `422` about members                | Group 1 is asha, kabir, meera, ravi; group 2 is neha, omar. | Use members of the group in the URL.                     |
| `400` for 1000.5                   | Amounts are whole paise.                                    | Send 1000 or 1001.                                       |
| `release version 25 not supported` | Maven is using an older JDK.                                | Point `JAVA_HOME` at JDK 25, or add `-Djava.version=21`. |

## Project layout

``` tree
stations/015-splitting-a-group-bill/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/splitsaathi/groups/
│   ├── GroupController.java   ├── Splitter.java   ├── SettleUp.java
│   ├── Groups.java            ├── ExpenseRequest.java   └── GroupsApplication.java
├── src/test/java/com/splitsaathi/groups/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/splitsaathi/groups/GroupController.java`

Does  
Validates the expense for its split type, splits it, stores it; answers settle-up.

Why  
A `switch` on the split type: the compiler checks every type is handled.

Without it  
No API.

#### `src/main/java/com/splitsaathi/groups/Splitter.java`

Does  
Equal and share-based splits in whole paise that always add up.

Why  
The money rule lives in one small, heavily tested class.

Without it  
The trap: rounded shares that do not add up.

- `total / n` and `total % n`: the quotient and the remainder, in exact integers.
- Shares: whole part first, then the leftover paise to the biggest cut-off fractions.

#### `src/main/java/com/splitsaathi/groups/SettleUp.java`

Does  
Greedy settle-up: biggest debtor pays biggest creditor until all are zero.

Why  
Each payment clears at least one person: at most n − 1 payments.

Without it  
One payment per person per expense.

- Refuses balances that do not add up to zero: a bug elsewhere must not become wrong payments.
- A `TreeMap` makes ties resolve the same way every time.

#### `src/main/java/com/splitsaathi/groups/Groups.java`

Does  
Groups, members and expenses (with their split stored); computes net balances.

Why  
Splitting once and storing the result means balances never re-divide.

Without it  
Balances recomputed from rounded shares.

#### `src/main/java/com/splitsaathi/groups/ExpenseRequest.java`

The body, with the split type as an enum.

#### `src/main/resources/application.yaml`

Problem bodies for every error; a fraction of a paisa is a `400`, not silently truncated.

#### `src/main/java/com/splitsaathi/groups/GroupsApplication.java`

Standard Spring Boot entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                    | Test class                 | Result |
|---------------|----------------------------------------------------------------|----------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                       | `ExpenseContractTest` (9)  | pass   |
| Every station | Reproduce the failure before the fix                           | `MissingPaisaTrapTest` (3) | pass   |
| This station  | The money rules on 1,000 generated cases; settle-up clears all | `SplitterTest` (3)         | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 9, Failures: 0, Errors: 0, Skipped: 0 -- in com.splitsaathi.groups.ExpenseContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.splitsaathi.groups.MissingPaisaTrapTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.splitsaathi.groups.SplitterTest
[INFO] Tests run: 15, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/splitsaathi/groups/MissingPaisaTrapTest.java`

Written first: the lost paisa with `double` and with rounded `BigDecimal`; the splitter keeps it.

#### `src/test/java/com/splitsaathi/groups/ExpenseContractTest.java`

Each split type, a trip settled in 3 payments, and every refusal.

#### `src/test/java/com/splitsaathi/groups/SplitterTest.java`

Largest remainder by hand, 1,000 random splits with a fixed seed, and settle-up clearing every balance.

#### `src/test/java/com/splitsaathi/groups/ApiTest.java`

Shared setup: the whole app through MockMvc, no expenses before each test.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/splitsaathi/groups/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=PercentSplitChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 15 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 19 tests pass (15 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Split by percentage

Add `PERCENT` with a `percents` map of whole percentages that must add up to 100.

**Done when:** both tests in `PercentSplitChallengeTest` pass, and the station's tests still pass.

Hints

- Percentages are shares out of 100: `Splitter.shares` already does the arithmetic, remainder included.
- Check the sum is exactly 100 before splitting; otherwise `422`.

#### `challenge/PercentSplitChallengeTest.java`

``` code
package com.splitsaathi.groups;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: a PERCENT split, with whole percentages that must add up to 100. */
class PercentSplitChallengeTest extends ApiTest {

    @Test
    void percentagesSplitTheAmountExactly() throws Exception {
        expense(1, """
                {"description":"Cake","paidBy":"meera","amountPaise":100001,"splitType":"PERCENT","percents":{"asha":33,"ravi":33,"meera":34}}""")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.owedPaise.asha").value(33000))
                .andExpect(jsonPath("$.owedPaise.ravi").value(33000))
                .andExpect(jsonPath("$.owedPaise.meera").value(34001));  // 34,000.34: the leftover paisa has the largest cut-off
    }

    @Test
    void percentagesThatDoNotAddUpTo100Are422() throws Exception {
        expense(1, """
                {"description":"Cake","paidBy":"meera","amountPaise":100000,"splitType":"PERCENT","percents":{"asha":33,"ravi":33,"meera":33}}""")
                .andExpect(status().isUnprocessableContent());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Record a settlement

Add `POST /groups/{id}/settlements` with `{"from", "to", "amountPaise"}`: Ravi paid Asha back. Balances move towards zero; after the suggested payments are recorded, settle-up suggests nothing.

**Done when:** both tests in `SettlementChallengeTest` pass.

Hints

- For the balances, "Ravi paid Asha ₹300" is an expense that Ravi paid and Asha alone owes. No new kind of record is needed.
- Refuse a payment to yourself and anyone outside the group.

#### `challenge/SettlementChallengeTest.java`

``` code
package com.splitsaathi.groups;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: POST /groups/{id}/settlements records a payment between two members, so balances move towards zero. */
class SettlementChallengeTest extends ApiTest {

    void settle(String from, String to, long paise, int expectedStatus) throws Exception {
        mvc.perform(post("/groups/1/settlements").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"from\":\"" + from + "\",\"to\":\"" + to + "\",\"amountPaise\":" + paise + "}"))
                .andExpect(status().is(expectedStatus));
    }

    @Test
    void payingTheSuggestedPaymentsLeavesNothingToSettle() throws Exception {
        expense(1, """
                {"description":"Dinner","paidBy":"asha","amountPaise":90000,"splitType":"EQUAL","participants":["asha","ravi","meera"]}""");
        settle("ravi", "asha", 30000, 201);
        mvc.perform(get("/groups/1/settle-up"))
                .andExpect(jsonPath("$.balancesPaise.ravi").value(0))
                .andExpect(jsonPath("$.payments", hasSize(1)));
        settle("meera", "asha", 30000, 201);
        mvc.perform(get("/groups/1/settle-up")).andExpect(jsonPath("$.payments", hasSize(0)));
    }

    @Test
    void badSettlementsAreRefused() throws Exception {
        settle("ravi", "ravi", 100, 422);     // to yourself
        settle("ravi", "neha", 100, 422);     // not in this group
        settle("ravi", "asha", 0, 400);       // nothing paid
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Who gets the extra paisa?

This station gives leftover paise to the first person listed. Over a year, that can be the same person every time. Propose a fairer rule (for example, rotating, or giving it to the payer), and check it still always adds up. Would you show the extra paisa in the app, or hide it?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: `double` and rounded `BigDecimal` both lose a paisa.
2.  Write the splitter in whole paise, with a fixed remainder rule; test it on 1,000 generated cases.
3.  Store each expense's split; compute balances by adding paid and subtracting owed.
4.  Write the greedy settle-up and prove it clears every balance.

## Design alternatives and trade-offs

| Approach                              | What it costs                                                                      | Verdict         |
|---------------------------------------|------------------------------------------------------------------------------------|-----------------|
| Whole paise + explicit remainder rule | A rule to decide who gets the leftover.                                            | Chosen          |
| `double` and round each share         | Loses or invents paise (the trap).                                                 | Wrong           |
| `BigDecimal` divided to 2 decimals    | Exact arithmetic, same lost paisa, because each share is still rounded separately. | Not enough      |
| Settle each expense separately        | Many payments.                                                                     | Wrong           |
| Exact minimum number of payments      | A search over subsets; slow for large groups. The greedy bound is usually enough.  | Rarely worth it |

## Database design

None in this station. With a database: `expenses` (payer, amount) and `expense_shares` (expense, person, owed) with a check that shares add up to the expense, enforced in the same transaction that inserts them.

# 3 · Go deeper: Production

Money  
Every amount is an integer of paise; division happens once per expense, with the remainder given out by rule. A balance that does not add up to zero stops settle-up instead of producing wrong payments.

Trust  
Users compare totals to the paisa. Show each person's share, and why someone got the extra paisa.

Security  
No login here; real apps check the caller is a member of the group before showing balances.

Maintainability  
A new split type is one `switch` case; the compiler flags any switch that forgets it.

# 3 · Go deeper: Interview

## Interview takeaways

How do you split ₹1,000 three ways so it adds up?

Work in paise: 100,000 ÷ 3 = 33,333 remainder 1. Give everyone 33,333 and the leftover paisa to one person by a fixed rule. Shares are 33,334, 33,333 and 33,333.

Does BigDecimal fix rounding problems?

It fixes representation (0.1 is exact), not allocation. Dividing 1000 by 3 exactly throws; rounding each share to two decimals still loses a paisa. You must distribute the remainder.

What is the largest remainder method?

Give everyone the whole part of their exact share, then hand the leftover units, one each, to those whose fractions were largest.

How many payments does greedy settle-up need?

At most n − 1 for n people, because each payment brings at least one person to zero. The true minimum can be lower and is expensive to find in general.

Why test with 1,000 random cases?

Hand-picked examples confirm what you already thought of. Generated cases, with a fixed seed so failures repeat, check the invariant everywhere: parts always add up to the total.

## Self-check rubric

| Area        | Meets the bar                            | Above the bar                                       |
|-------------|------------------------------------------|-----------------------------------------------------|
| Correctness | All 15 tests pass.                       | You can split any amount by shares by hand.         |
| Money       | Integers and an explicit remainder rule. | You can explain why rounded BigDecimal still fails. |
| Tests       | An invariant tested on generated cases.  | You know why the seed is fixed.                     |
| Explanation | Greedy settle-up in two sentences.       | You can state and justify its n − 1 bound.          |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any money-splitting code:

- Is any amount a `double`?
- Is each part rounded separately? Who gets the remainder?
- Is there a test that the parts add up, on many cases?
- What happens if balances do not add up to zero?
