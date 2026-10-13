# Station 016 · Loan EMI calculator and schedule

Foundations · 0–1 years · Core · Fintech · Types: none

Spring Boot 4.1.1 · Java 25 · Spring MVC · BigDecimal · MathContext · TreeMap · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** A quote is a record in the app's memory. No loan is sanctioned and no money moves. The rates are demo numbers, not any bank's, and nothing here is financial advice.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 12 tests.

# 1 · Understand

## The problem in real life

1.  **Meera checks her EMI in the Tijori app**

    ₹5 lakh, 24 months, 12.99%: the app says ₹23,766. The bank's letter says ₹23,769. She asks support which one is wrong.

2.  **Two years later**

    The app's schedule shows her last month leaving a balance of −₹11.91: she would have paid more than she owed, and the loan never shows "closed".

3.  **The fix**

    Compute the formula with full precision and round once, at the end. Then work out each month's interest on what is left, and let the last instalment pay exactly the remainder.

Round once, as late as possible, and let the last instalment absorb what rounding left behind.

## What are we building?

`POST /loan-quotes` takes a product, an amount and a tenure, picks the rate valid today, and returns the EMI and the totals. `GET /loan-quotes/{id}/schedule` shows every month: interest, principal and the balance, ending at exactly zero.

## An everyday analogy

Paying back a friend ₹1,000 in three goes: you say "₹334 each time". After two payments you owe ₹332, not ₹334. You pay ₹332 the last time; you don't pay ₹334 and ask for ₹2 back.

## How it works in 4 steps

1.  **Pick the rate** valid on today's date for the product.
2.  **Compute the EMI** with the formula, every step at full precision; round once, to whole rupees.
3.  **Walk the months**: interest on what is left, the rest of the EMI repays principal.
4.  **Close the loan**: the month that would go below zero pays only what is left.

Check yourself: the EMI was rounded up from ₹23,768.56 to ₹23,769. Does the customer pay too much?

Each month a little more principal is repaid, so the last instalment is smaller by exactly the overpayment: ₹23,757.09. In total they pay interest only on what they actually owed.

## What this station is not

- **Not a real loan.** No sanction, no credit check, no money moves.
- **Not a bank's exact method.** Real lenders add processing fees, broken-period interest for the first month and their own rounding rules.
- **No database.** Quotes live in memory and are gone when the app stops.

## Key terms

| Term                      | Simple meaning                                                                                         | Everyday example                                        | In this project                      |
|---------------------------|--------------------------------------------------------------------------------------------------------|---------------------------------------------------------|--------------------------------------|
| **EMI**                   | Equated Monthly Instalment: the same payment every month that repays a loan with its interest.         | ₹23,769 a month for 2 years on a ₹5 lakh personal loan. | `emiPaise`                           |
| **Principal**             | The amount borrowed. Each EMI repays part of it.                                                       | The ₹5 lakh itself.                                     | `principalPaise`                     |
| **Interest for a month**  | What is still owed × the yearly rate ÷ 12.                                                             | ₹5,00,000 × 12.99% ÷ 12 = ₹5,412.50 in month 1.         | `interestPaise` in each row          |
| **Amortisation schedule** | A month-by-month table: how much of each EMI is interest, how much repays principal, and what is left. | The table a bank attaches to the loan agreement.        | `GET /loan-quotes/{id}/schedule`     |
| **Final adjustment**      | The last instalment pays exactly what is left, so the loan closes at zero.                             | The last EMI is ₹11.91 smaller.                         | `lastEmiPaise`                       |
| **Dated rate**            | A rate that applies from a given day until the next one starts.                                        | "12.99% from 1 October".                                | `tijori.rates` in `application.yaml` |

# 2 · Build: Spec

## Business problem

**Tijori** (a fictional lending app) shows an EMI before the loan is booked. It differs from the bank's by ₹3, because the app rounds an intermediate step. Its schedule repeats the same rounded EMI every month, so the last month never closes the loan to zero. Both look like mistakes to customers, and both are.

## Acceptance criteria

1.  **Given** ₹5,00,000 at 12.99% for 24 months, **then** the EMI is ₹23,769 and the last instalment is ₹23,757.09.
2.  **Given** ₹1,00,000 at 12% for 12 months, **then** the EMI is ₹8,885 (the textbook ₹8,884.88, rounded).
3.  **Given** any schedule, **then** the principal parts add up to the loan exactly, no balance goes below zero, and the last balance is zero.
4.  **Given** a quote on 19 October 2026, **then** the personal-loan rate is 12.99% (valid from 1 October), not 13.50%.
5.  **Given** a product whose first rate starts later, **then** `422`.
6.  **Given** an amount or tenure out of range, **then** `400`; an unknown quote id, `404`.

## Requirements

- Amounts in paise: ₹10,000 to ₹1 crore (a demo rule). Tenure 6 to 360 months.
- The EMI is rounded half up to whole rupees, once. Monthly interest is rounded half up to the paisa.
- Rates come from configuration, each with a start date. A new rate is a new line, added ahead of time.
- The schedule is recomputed from the stored quote, with the rate the quote was given.

## Learning objectives

- Implement the EMI formula with `BigDecimal` and a `MathContext`.
- Explain where rounding happens, and why the last instalment differs.
- Build an amortisation schedule and test that it always closes at zero.
- Pick a dated value with `TreeMap.floorEntry`, and make "today" testable with a `Clock`.

# 2 · Build: API contract

## Endpoints

| Method | Path                         | Purpose                                                                |
|--------|------------------------------|------------------------------------------------------------------------|
| `POST` | `/loan-quotes`               | Quote a loan at today's rate. `201` with a `Location` to its schedule. |
| `GET`  | `/loan-quotes/{id}/schedule` | Month-by-month rows for a quote.                                       |

## Request body

| Field            | Rule                                                            |
|------------------|-----------------------------------------------------------------|
| `product`        | `PERSONAL`, `HOME` or `GOLD`.                                   |
| `principalPaise` | 1,000,000 to 1,000,000,000 (₹10,000 to ₹1 crore), whole number. |
| `tenureMonths`   | 6 to 360.                                                       |

## Response

| Field                                     | Meaning                                                                                       |
|-------------------------------------------|-----------------------------------------------------------------------------------------------|
| `annualRatePercent`, `rateValidFrom`      | The rate used, and the day it started.                                                        |
| `instalments`                             | How many payments. Usually the tenure; fewer when a rounded-up EMI repays a small loan early. |
| `emiPaise`, `lastEmiPaise`                | The monthly instalment, and the adjusted last one.                                            |
| `totalInterestPaise`, `totalPayablePaise` | Sums over the schedule, not EMI × months.                                                     |

## Status codes

| Status | When                                                  |
|--------|-------------------------------------------------------|
| 201    | Quote created                                         |
| 200    | Schedule                                              |
| 400    | A field is missing, out of range or of the wrong type |
| 404    | No quote with this id                                 |
| 422    | No rate for this product is valid today               |

## Captured examples

Captured with curl from the running app on 13 Oct 2026, in this order, so "today" is that date. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: ₹5 lakh personal loan, 24 months

**Why:** the 12.99% rate started on 1 October 2026. The EMI ₹23,768.56 is rounded once to ₹23,769; the last instalment is ₹11.91 smaller, so the total is less than 24 × EMI.

Request

``` code
POST /loan-quotes HTTP/1.1
Content-Type: application/json

{
  "product": "PERSONAL",
  "principalPaise": 50000000,
  "tenureMonths": 24
}
```

Response

``` code
HTTP/1.1 201 
Location: /loan-quotes/4a9db5e5-1c08-4e22-858c-e6676bac703f/schedule
Content-Type: application/json

{
  "quoteId": "4a9db5e5-1c08-4e22-858c-e6676bac703f",
  "product": "PERSONAL",
  "quoteDate": "2026-10-13",
  "principalPaise": 50000000,
  "tenureMonths": 24,
  "annualRatePercent": 12.99,
  "rateValidFrom": "2026-10-01",
  "instalments": 24,
  "emiPaise": 2376900,
  "lastEmiPaise": 2375709,
  "totalInterestPaise": 7044409,
  "totalPayablePaise": 57044409
}
```

### Case 2: its schedule

**Why:** each month's interest is on what is left, so the interest part shrinks and the principal part grows. Row 24 pays exactly the remaining balance and ends at 0.

Request

``` code
GET /loan-quotes/4a9db5e5-1c08-4e22-858c-e6676bac703f/schedule HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 2532

{
  "quoteId": "4a9db5e5-1c08-4e22-858c-e6676bac703f",
  "rows": [
    {
      "month": 1,
      "emiPaise": 2376900,
      "interestPaise": 541250,
      "principalPaise": 1835650,
      "balancePaise": 48164350
    },
    {
      "month": 2,
      "emiPaise": 2376900,
      "interestPaise": 521379,
      "principalPaise": 1855521,
      "balancePaise": 46308829
    },
    {
      "month": 3,
      "emiPaise": 2376900,
      "interestPaise": 501293,
      "principalPaise": 1875607,
      "balancePaise": 44433222
    },
    {
      "month": 4,
      "emiPaise": 2376900,
      "interestPaise": 480990,
      "principalPaise": 1895910,
      "balancePaise": 42537312
    },
    {
      "month": 5,
      "emiPaise": 2376900,
      "interestPaise": 460466,
      "principalPaise": 1916434,
      "balancePaise": 40620878
    },
    {
      "month": 6,
      "emiPaise": 2376900,
      "interestPaise": 439721,
      "principalPaise": 1937179,
      "balancePaise": 38683699
    },
    {
      "month": 7,
      "emiPaise": 2376900,
      "interestPaise": 418751,
      "principalPaise": 1958149,
      "balancePaise": 36725550
    },
    {
      "month": 8,
      "emiPaise": 2376900,
      "interestPaise": 397554,
      "principalPaise": 1979346,
      "balancePaise": 34746204
    },
    {
      "month": 9,
      "emiPaise": 2376900,
      "interestPaise": 376128,
      "principalPaise": 2000772,
      "balancePaise": 32745432
    },
    {
      "month": 10,
      "emiPaise": 2376900,
      "interestPaise": 354469,
      "principalPaise": 2022431,
      "balancePaise": 30723001
    },
    {
      "month": 11,
      "emiPaise": 2376900,
      "interestPaise": 332576,
      "principalPaise": 2044324,
      "balancePaise": 28678677
    },
    {
      "month": 12,
      "emiPaise": 2376900,
      "interestPaise": 310447,
      "principalPaise": 2066453,
      "balancePaise": 26612224
    },
    {
      "month": 13,
      "emiPaise": 2376900,
      "interestPaise": 288077,
      "principalPaise": 2088823,
      "balancePaise": 24523401
    },
    {
      "month": 14,
      "emiPaise": 2376900,
      "interestPaise": 265466,
      "principalPaise": 2111434,
      "balancePaise": 22411967
    },
    {
      "month": 15,
      "emiPaise": 2376900,
      "interestPaise": 242610,
      "principalPaise": 2134290,
      "balancePaise": 20277677
    },
    {
      "month": 16,
      "emiPaise": 2376900,
      "interestPaise": 219506,
      "principalPaise": 2157394,
      "balancePaise": 18120283
    },
    {
      "month": 17,
      "emiPaise": 2376900,
      "interestPaise": 196152,
      "principalPaise": 2180748,
      "balancePaise": 15939535
    },
    {
      "month": 18,
      "emiPaise": 2376900,
      "interestPaise": 172545,
      "principalPaise": 2204355,
      "balancePaise": 13735180
    },
    {
      "month": 19,
      "emiPaise": 2376900,
      "interestPaise": 148683,
      "principalPaise": 2228217,
      "balancePaise": 11506963
    },
    {
      "month": 20,
      "emiPaise": 2376900,
      "interestPaise": 124563,
      "principalPaise": 2252337,
      "balancePaise": 9254626
    },
    {
      "month": 21,
      "emiPaise": 2376900,
      "interestPaise": 100181,
      "principalPaise": 2276719,
      "balancePaise": 6977907
    },
    {
      "month": 22,
      "emiPaise": 2376900,
      "interestPaise": 75536,
      "principalPaise": 2301364,
      "balancePaise": 4676543
    },
    {
      "month": 23,
      "emiPaise": 2376900,
      "interestPaise": 50624,
      "principalPaise": 2326276,
      "balancePaise": 2350267
    },
    {
      "month": 24,
      "emiPaise": 2375709,
      "interestPaise": 25442,
      "principalPaise": 2350267,
      "balancePaise": 0
    }
  ]
}
```

### Case 3: ₹50 lakh home loan, 20 years

**Why:** month 1's interest alone is ₹35,416.67 of the ₹43,391 EMI: long loans repay little principal at first.

Request

``` code
POST /loan-quotes HTTP/1.1
Content-Type: application/json

{
  "product": "HOME",
  "principalPaise": 500000000,
  "tenureMonths": 240
}
```

Response

``` code
HTTP/1.1 201 
Location: /loan-quotes/bc9f1f17-ae3a-4894-a13f-b3e1d62780ec/schedule
Content-Type: application/json

{
  "quoteId": "bc9f1f17-ae3a-4894-a13f-b3e1d62780ec",
  "product": "HOME",
  "quoteDate": "2026-10-13",
  "principalPaise": 500000000,
  "tenureMonths": 240,
  "annualRatePercent": 8.5,
  "rateValidFrom": "2026-04-01",
  "instalments": 240,
  "emiPaise": 4339100,
  "lastEmiPaise": 4349255,
  "totalInterestPaise": 541394155,
  "totalPayablePaise": 1041394155
}
```

### Case 4: ₹10,000 for 30 years

**Why:** ₹110.54 rounds up to ₹111; 46 paise more each month repays the loan in 344 instalments, not 360. The schedule stops when the balance reaches zero instead of going below it.

Request

``` code
POST /loan-quotes HTTP/1.1
Content-Type: application/json

{
  "product": "PERSONAL",
  "principalPaise": 1000000,
  "tenureMonths": 360
}
```

Response

``` code
HTTP/1.1 201 
Location: /loan-quotes/aa8adf06-acdb-49f0-ab22-00987d7d0782/schedule
Content-Type: application/json

{
  "quoteId": "aa8adf06-acdb-49f0-ab22-00987d7d0782",
  "product": "PERSONAL",
  "quoteDate": "2026-10-13",
  "principalPaise": 1000000,
  "tenureMonths": 360,
  "annualRatePercent": 12.99,
  "rateValidFrom": "2026-10-01",
  "instalments": 344,
  "emiPaise": 11100,
  "lastEmiPaise": 4945,
  "totalInterestPaise": 2812245,
  "totalPayablePaise": 3812245
}
```

### Case 5: a product with no rate today

**Why:** the gold-loan rate starts on 1 January 2027. No rate is guessed: `422`.

Request

``` code
POST /loan-quotes HTTP/1.1
Content-Type: application/json

{
  "product": "GOLD",
  "principalPaise": 10000000,
  "tenureMonths": 12
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "There is no GOLD rate valid on 2026-10-13.",
  "instance": "/loan-quotes",
  "status": 422,
  "title": "No rate on this date"
}
```

### Case 6: 3 months

**Why:** below the 6-month minimum: `400`. Spring's default detail does not say which field; station 006 shows how to add that.

Request

``` code
POST /loan-quotes HTTP/1.1
Content-Type: application/json

{
  "product": "PERSONAL",
  "principalPaise": 50000000,
  "tenureMonths": 3
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Invalid request content.",
  "instance": "/loan-quotes",
  "status": 400,
  "title": "Bad Request"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                         | What happens                                                        | Proved by                                                             |
|----------------------------------------------|---------------------------------------------------------------------|-----------------------------------------------------------------------|
| ₹1,00,000 at 12% for 12 months               | EMI ₹8,885                                                          | `aTextbookExample`                                                    |
| 80 combinations of amount, rate and tenure   | Each closes at 0, repays the principal exactly, never goes negative | `everyCombinationClosesAtZeroAndRepaysThePrincipalExactly`            |
| ₹10,000 at 12.99% for 360 months             | Repaid in 344 instalments                                           | `aSmallLongLoanWhoseEmiWasRoundedUpClosesEarlyInsteadOfGoingNegative` |
| The day before and the day a new rate starts | Old rate; new rate                                                  | `theRateIsTheOneValidOnTheDay`                                        |
| ₹5 lakh personal loan                        | 201, 12.99%, last EMI 11.91 smaller                                 | `aQuoteUsesTheRateValidTodayAndPointsToItsSchedule`                   |
| ₹50 lakh home loan, 240 months               | 240 rows; month 1 interest ₹35,416.67; ends at 0                    | `theScheduleHasOneRowPerMonthAndEndsAtZero`                           |
| GOLD before its first rate                   | `422`                                                               | `aProductWithNoRateYetIs422`                                          |
| ₹9,999.99; 5 or 361 months; CAR; empty body  | `400`                                                               | `outOfRangeOrMissingFieldsAre400`                                     |
| Unknown quote id                             | `404`                                                               | `anUnknownQuoteIs404`                                                 |

## The trap

Plausible but wrong

Rounding every instalment the same way, so the last one never closes the loan.

A schedule that subtracts the same rounded EMI 24 times ends at −1,191 paise: the customer overpays ₹11.91. A calculator that keeps four decimals turns `(1+r)^24` = 1.294862 into 1.2949 and quotes ₹23,766 instead of ₹23,769: the ₹3 support tickets. The real schedule rounds once and adjusts the last instalment. Removing the final adjustment and the cap while building turned 5 tests red. Testing every combination also found a second case: a small loan over 30 years whose rounded-up EMI repays it before month 360. That month now pays only what is left, and the schedule ends there.

``` code
package com.tijori.loans;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The first test written for this station: it reproduces the bugs before the fix.
 * A Rs 5,00,000 personal loan at 12.99% a year, over 24 months.
 */
class LastInstalmentTrapTest {

    static final long PRINCIPAL = 50_000_000;
    static final BigDecimal RATE = new BigDecimal("12.99");

    /** The "before" schedule: the same rounded EMI every month, including the last. Kept only in tests. */
    static long oldFinalBalance() {
        long emi = Emi.emiPaise(PRINCIPAL, RATE, 24);
        BigDecimal r = Emi.monthlyRate(RATE);
        long balance = PRINCIPAL;
        for (int m = 1; m <= 24; m++) {
            long interest = BigDecimal.valueOf(balance).multiply(r).setScale(0, RoundingMode.HALF_UP).longValueExact();
            balance -= emi - interest;
        }
        return balance;
    }

    @Test
    void theSameEmiEveryMonthNeverLandsOnZero() {
        assertThat(oldFinalBalance()).isEqualTo(-1_191);   // the customer overpays Rs 11.91 and the loan shows a negative balance
    }

    /** The "before" EMI: a calculator that keeps four decimals and rounds (1+r)^24 = 1.294862 to 1.2949 before dividing. */
    static long oldEmiPaise() {
        BigDecimal r = Emi.monthlyRate(RATE);
        BigDecimal growth = BigDecimal.ONE.add(r).pow(24).setScale(4, RoundingMode.HALF_UP);
        BigDecimal emi = BigDecimal.valueOf(PRINCIPAL, 2).multiply(r).multiply(growth)
                .divide(growth.subtract(BigDecimal.ONE), 10, RoundingMode.HALF_UP);
        return emi.setScale(0, RoundingMode.HALF_UP).movePointRight(2).longValueExact();
    }

    @Test
    void roundingAnIntermediateStepMovesTheEmiByThreeRupees() {
        assertThat(oldEmiPaise()).isEqualTo(2_376_600);                       // Rs 23,766: what the app showed
        assertThat(Emi.emiPaise(PRINCIPAL, RATE, 24)).isEqualTo(2_376_900);   // Rs 23,769: what the bank charges
    }

    @Test
    void theRealScheduleAdjustsTheLastInstalmentAndClosesAtZero() {
        List<Emi.Row> rows = Emi.schedule(PRINCIPAL, RATE, 24);
        assertThat(rows).hasSize(24);
        assertThat(rows.getLast().balancePaise()).isZero();
        assertThat(rows.getLast().emiPaise()).isEqualTo(2_376_900 - 1_191);   // the overpayment is taken off the last EMI
        assertThat(rows.stream().mapToLong(Emi.Row::principalPaise).sum()).isEqualTo(PRINCIPAL);
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
./mvnw test                 # all 12 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

The body is in `docs/personal-loan.json` (₹5 lakh, 24 months).

``` code
# Quote: expect emiPaise 2376900 and lastEmiPaise 2375709 (at the 12.99% rate valid from 1 Oct 2026)
curl -i -X POST http://localhost:8080/loan-quotes -H "Content-Type: application/json" -d "@docs/personal-loan.json"

# The schedule: use the Location header from the quote
curl http://localhost:8080/loan-quotes/<id>/schedule
```

## Troubleshooting

| You see                            | Cause                                | Fix                                                              |
|------------------------------------|--------------------------------------|------------------------------------------------------------------|
| A different rate than the examples | Rates depend on today's date.        | Check `tijori.rates`: the latest `from` on or before today wins. |
| `422` for GOLD                     | Its first rate starts on 1 Jan 2027. | Add an earlier line in `application.yaml` to experiment.         |
| `release version 25 not supported` | Maven is using an older JDK.         | Point `JAVA_HOME` at JDK 25, or add `-Djava.version=21`.         |

## Project layout

``` tree
stations/016-loan-emi-calculator-and-schedule/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tijori/loans/
│   ├── LoanQuoteController.java   ├── Emi.java   ├── RateTable.java
│   ├── Product.java               └── LoansApplication.java
├── src/main/resources/application.yaml   the dated rates
├── src/test/java/com/tijori/loans/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/tijori/loans/LoanQuoteController.java`

Does  
Validates the request, picks today's rate, builds the schedule once for the totals, stores the quote.

Why  
Totals are sums over the real schedule, so they include the adjusted last instalment.

Without it  
EMI × months as the total payable.

#### `src/main/java/com/tijori/loans/Emi.java`

Does  
The formula and the schedule, in `BigDecimal`.

Why  
All money arithmetic in one small class with its own tests.

Without it  
The trap: rounding early, and the same EMI every month.

- `MathContext.DECIMAL128`: 34 significant digits for every step, so rounding only happens where the code says.
- The EMI is rounded once; each month's interest is rounded to the paisa.
- The last month, or any month that would go below zero, pays exactly what is left.

#### `src/main/java/com/tijori/loans/RateTable.java`

Does  
Dated rates from `application.yaml`; the rate on a day.

Why  
`TreeMap.floorEntry(date)` is "the latest start date on or before this day" in one call.

Without it  
A single rate per product, edited on the day it changes.

#### `src/main/java/com/tijori/loans/Product.java`

The three products. An unknown name is a `400`.

#### `src/main/resources/application.yaml`

The dated rates (demo numbers), problem bodies for errors, and no silent truncation of `2.5` to `2`.

#### `src/main/java/com/tijori/loans/LoansApplication.java`

Entry point, and the `Clock` in India's time zone, so tests can fix "today".

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                | Test class                   | Result |
|---------------|------------------------------------------------------------|------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                   | `LoanQuoteContractTest` (5)  | pass   |
| Every station | Reproduce the failure before the fix                       | `LastInstalmentTrapTest` (3) | pass   |
| This station  | The formula, every combination closing at zero, rate dates | `EmiTest` (4)                | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.loans.LastInstalmentTrapTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.loans.EmiTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.loans.LoanQuoteContractTest
[INFO] Tests run: 12, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/tijori/loans/LastInstalmentTrapTest.java`

Written first: −₹11.91 left by the same EMI every month, ₹3 lost by an early rounding, and the real schedule closing at zero.

#### `src/test/java/com/tijori/loans/LoanQuoteContractTest.java`

A quote at today's rate, its schedule, and every refusal.

#### `src/test/java/com/tijori/loans/EmiTest.java`

A textbook value, 80 combinations that must close at zero, a loan that closes early, and rates on their boundary days.

#### `src/test/java/com/tijori/loans/ApiTest.java`

Shared setup: the whole app through MockMvc, with "today" fixed at 19 Oct 2026 by a test `Clock`.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/tijori/loans/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=PrepaymentChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 12 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 18 tests pass (12 station tests and 6 challenge tests).

Challenge 1 · Go deeper · about 35 minutes

## Part-prepayment

Add `?prepayMonth=6&prepayPaise=10000000` to the schedule: ₹1 lakh paid after month 6's EMI. Keep the EMI; the loan ends sooner. Each row gets `prepaidPaise`.

**Done when:** all three tests in `PrepaymentChallengeTest` pass: 20 instalments instead of 24.

Hints

- The schedule already stops when the balance reaches zero; a prepayment only lowers the balance one month.
- Refuse a prepayment that would clear the whole balance (that is a foreclosure), or one after the last EMI: `422`.
- One parameter without the other is a `400`.

#### `challenge/PrepaymentChallengeTest.java`

``` code
package com.tijori.loans;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /loan-quotes/{id}/schedule?prepayMonth=6&prepayPaise=10000000 shows the schedule with a part-prepayment
 * made after that month's EMI. The EMI stays the same, so the loan ends sooner. Each row gets a prepaidPaise field.
 */
class PrepaymentChallengeTest extends ApiTest {

    String personalLoan() throws Exception {
        return quote("PERSONAL", 50_000_000, 24).andReturn().getResponse().getHeader("Location");
    }

    @Test
    void aPrepaymentKeepsTheEmiAndShortensTheLoan() throws Exception {
        mvc.perform(get(personalLoan()).param("prepayMonth", "6").param("prepayPaise", "10000000"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.rows", hasSize(20)))                        // 20 instalments, not 24
                .andExpect(jsonPath("$.rows[5].emiPaise").value(2_376_900))
                .andExpect(jsonPath("$.rows[5].prepaidPaise").value(10_000_000))
                .andExpect(jsonPath("$.rows[5].balancePaise").value(28_683_699))   // 3,86,836.99 - 1,00,000
                .andExpect(jsonPath("$.rows[6].emiPaise").value(2_376_900))        // same EMI after the prepayment
                .andExpect(jsonPath("$.rows[19].emiPaise").value(4_633))           // the last one is small
                .andExpect(jsonPath("$.rows[19].balancePaise").value(0));
    }

    @Test
    void withoutAPrepaymentTheScheduleIsUnchanged() throws Exception {
        mvc.perform(get(personalLoan()))
                .andExpect(jsonPath("$.rows", hasSize(24)))
                .andExpect(jsonPath("$.rows[5].prepaidPaise").value(0))
                .andExpect(jsonPath("$.rows[23].balancePaise").value(0));
    }

    @Test
    void impossiblePrepaymentsAreRefused() throws Exception {
        String loan = personalLoan();
        mvc.perform(get(loan).param("prepayMonth", "6").param("prepayPaise", "38683699"))   // all that is left: that is a foreclosure
                .andExpect(status().isUnprocessableContent());
        mvc.perform(get(loan).param("prepayMonth", "24").param("prepayPaise", "100000"))    // after the last EMI
                .andExpect(status().isUnprocessableContent());
        mvc.perform(get(loan).param("prepayMonth", "6"))                                     // amount missing
                .andExpect(status().isBadRequest());
        mvc.perform(get(loan).param("prepayMonth", "6").param("prepayPaise", "0"))
                .andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Beginner-friendly · about 20 minutes

## Quote for a disbursal date

Add an optional `disbursalDate`. The rate is the one valid on that date, so a gold loan disbursed on 5 Jan 2027 can be quoted today. Demo rule: today to 90 days ahead.

**Done when:** all three tests in `DisbursalDateChallengeTest` pass.

Hints

- `rateOn` already takes a date: pass the disbursal date instead of today.
- A `LocalDate` field in the body is parsed from `2027-01-05`; any other format is a `400` on its own.

#### `challenge/DisbursalDateChallengeTest.java`

``` code
package com.tijori.loans;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: an optional disbursalDate in the request. The quote uses the rate valid on that date, not today.
 * Demo rule: the date is today or up to 90 days ahead. Without it, nothing changes.
 */
class DisbursalDateChallengeTest extends ApiTest {

    ResultActions quoteOn(String product, String date) throws Exception {
        return mvc.perform(post("/loan-quotes").contentType(MediaType.APPLICATION_JSON).content(
                "{\"product\":\"" + product + "\",\"principalPaise\":10000000,\"tenureMonths\":12,\"disbursalDate\":\"" + date + "\"}"));
    }

    @Test
    void theRateIsTheOneValidOnTheDisbursalDate() throws Exception {
        quoteOn("GOLD", "2027-01-05")                                   // today (19 Oct 2026) GOLD has no rate yet
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.disbursalDate").value("2027-01-05"))
                .andExpect(jsonPath("$.annualRatePercent").value(9.25))
                .andExpect(jsonPath("$.rateValidFrom").value("2027-01-01"));
        quoteOn("GOLD", "2026-12-31").andExpect(status().isUnprocessableContent());   // the day before it starts
    }

    @Test
    void withoutADateItIsToday() throws Exception {
        quote("PERSONAL", 10_000_000, 12).andExpect(jsonPath("$.disbursalDate").value("2026-10-19"));
    }

    @Test
    void aPastOrFarDateIsRefused() throws Exception {
        quoteOn("PERSONAL", "2026-10-18").andExpect(status().isUnprocessableContent());   // yesterday
        quoteOn("PERSONAL", "2027-01-17").andExpect(status().isCreated());                // day 90
        quoteOn("PERSONAL", "2027-01-18").andExpect(status().isUnprocessableContent());   // day 91
        quoteOn("PERSONAL", "18-10-2026").andExpect(status().isBadRequest());             // not ISO 8601
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Lower EMI or shorter loan?

After a prepayment, lenders often offer a choice: keep the EMI and shorten the tenure, or keep the tenure and lower the EMI. Sketch both schedules for the challenge 1 loan. Which saves more interest, and why? What would the API need to let the customer choose, and what must the quote show before they do?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the same EMI every month ends at −₹11.91; an early rounding costs ₹3.
2.  Write the formula in `BigDecimal` with one `MathContext`; check it against a textbook value.
3.  Write the schedule with the final adjustment; test 80 combinations for zero, exact principal, no negative balance.
4.  Move rates into configuration with start dates; inject a `Clock`.

## Design alternatives and trade-offs

| Approach                                 | What it costs                                                                                              | Verdict           |
|------------------------------------------|------------------------------------------------------------------------------------------------------------|-------------------|
| `BigDecimal` + `MathContext`, round once | Verbose arithmetic.                                                                                        | Chosen            |
| `double` and `Math.pow`                  | Fine for the EMI shown to 2 decimals most of the time; wrong at the paisa now and then, and hard to prove. | Not for money     |
| Rounding each step to 2 or 4 decimals    | Small errors grow through the power and the division: the ₹3 bug.                                          | Wrong             |
| EMI to the paisa instead of whole rupees | Last instalment differs less, but still differs: the adjustment is still needed.                           | A lender's choice |
| Rates hard-coded in Java                 | A release for every rate change, and old quotes can no longer be explained.                                | Wrong             |

## Database design

None in this station. With a database: `rates` (product, valid_from, annual_percent) with a unique key on (product, valid_from) and a check that the rate is positive; `quotes` store the rate itself, not a reference that could change.

# 3 · Go deeper: Production

Money  
Paise in, paise out; `BigDecimal` only in between. Totals come from the schedule, so the quote and the schedule can never disagree.

Rates  
A new rate is added before its start date, never edited in place: a quote can always be explained by the rate valid on its date.

Time  
"Today" is in India's time zone. A server in UTC would quote the old rate for the first five and a half hours of the day a rate changes.

Regulation  
Real lenders must show the rate, fees and total cost in a key fact statement before the loan. This station shows how the numbers are computed, not the full disclosure.

# 3 · Go deeper: Interview

## Interview takeaways

What is the EMI formula?

EMI = P × r × (1+r)^n ÷ ((1+r)^n − 1), where P is the principal, r the monthly rate (annual ÷ 12 ÷ 100) and n the number of months.

Why does the last instalment differ?

The EMI is rounded, so every month repays a little more or less principal than the exact formula. The last instalment pays exactly what is left, so the loan closes at zero.

Why BigDecimal with a MathContext?

BigDecimal is exact for decimals, but dividing can need infinitely many digits. A MathContext says how many significant digits to keep, so the code controls where rounding happens.

How do you find the rate valid on a date?

Keep rates in a TreeMap keyed by start date and call floorEntry(date): the latest start on or before that day.

Why inject a Clock?

So tests can fix today and check the rate on a boundary day, instead of tests that pass or fail depending on when they run.

## Self-check rubric

| Area        | Meets the bar                                                      | Above the bar                                             |
|-------------|--------------------------------------------------------------------|-----------------------------------------------------------|
| Correctness | All 12 tests pass.                                                 | You can compute month 1's interest and principal by hand. |
| Money       | Rounding happens once for the EMI and once per month for interest. | You can explain the ₹3 and the ₹11.91.                    |
| Tests       | A schedule invariant tested on many combinations.                  | You can say what bug those combinations found.            |
| Explanation | The final adjustment in two sentences.                             | Lower EMI vs shorter loan after a prepayment.             |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any loan or interest code:

- Is any amount or rate a `double`?
- Where does rounding happen, and how many times?
- Does the schedule end at exactly zero, for every amount and tenure tested?
- Where do rates come from, and which one applies on the day a rate changes?
