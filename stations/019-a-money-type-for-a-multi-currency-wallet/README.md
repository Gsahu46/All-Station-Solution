# Station 019 · A Money type for a multi-currency wallet

Foundations · 0–1 years · Core · Fintech · Types: none

Spring Boot 4.1.1 · Java 25 · Spring MVC · records as value objects · BigDecimal · java.util.Currency · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Wallet balances are numbers in the app's memory. A credit creates a record; no money moves, no currency is bought or sold, and there are no exchange rates in the station itself.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 13 tests.

# 1 · Understand

## The problem in real life

1.  **Asha gets ₹100 of cashback and a \$5 refund**

    The wallet shows a balance of 105. Of what? The app treats it as rupees.

2.  **A reconciliation check fails**

    The ledger says ₹10.5, the bank file says ₹10.50, and the code says they are different amounts, because `BigDecimal.equals` compares the number of decimals too.

3.  **The fix**

    A `Money` type that stores whole minor units with its currency, refuses to add different currencies, and is compared by value. The wallet keeps one balance per currency.

An amount without its currency is not money. Make the type carry both, and compare by value.

## What are we building?

`POST /wallets/{id}/credits` adds an amount in one currency. `GET /wallets/{id}/balance` shows one balance per currency, each with that currency's own number of decimals.

## An everyday analogy

A travel pouch with one pocket per currency. Rupees go in the rupee pocket and dollars in the dollar pocket. Nobody counts them together without first asking at what rate.

## How it works in 4 steps

1.  **Read the amount as text**, like `"10.5"`, with its currency code.
2.  **Convert to minor units** for that currency: 1,050 paise. Refuse anything that would lose a digit.
3.  **Add to that currency's pocket**; adding a different currency is an error in the type itself.
4.  **Show each pocket** with the currency's own decimals: `10.50` INR, `1500` JPY.

Check yourself: is ₹10.5 the same as ₹10.50? Is 10.50 rupees the same as 10.50 dollars?

Yes, then no. Same value in the same currency is the same money, whatever the trailing zeros. The same number in two currencies is two different things.

## What this station is not

- **No currency exchange.** Balances are never added across currencies (challenge 2 adds an indicative total at demo rates).
- **No debits.** Challenge 1 adds them.
- **No database.** Two demo wallets live in memory.

## Key terms

| Term              | Simple meaning                                                                     | Everyday example                                                    | In this project                       |
|-------------------|------------------------------------------------------------------------------------|---------------------------------------------------------------------|---------------------------------------|
| **Value object**  | An object defined only by its values: two with the same values are the same thing. | Two ₹10 notes are interchangeable.                                  | `record Money`                        |
| **Minor unit**    | The smallest unit of a currency: paise, cents. Some currencies have none.          | ₹10.50 is 1,050 paise; ¥1,500 is just 1,500.                        | `minorUnits`                          |
| **Scale**         | How many digits a `BigDecimal` keeps after the point.                              | 10.5 has scale 1; 10.50 has scale 2.                                | Why `equals` differs from `compareTo` |
| **ISO 4217**      | The standard list of currency codes and their minor units.                         | INR, USD, AED (2 decimals); JPY (0).                                | `java.util.Currency`                  |
| **Immutable**     | Never changes after it is made; operations return a new one.                       | Adding to a ₹10 note does not change the note: you get a new total. | `plus` returns a new `Money`          |
| **Currency-safe** | Arithmetic that refuses to mix currencies.                                         | A cashier does not add rupees and dollars into one number.          | `CurrencyMismatchException`           |

# 2 · Build: Spec

## Business problem

**Tijori** (a fictional fintech app) added foreign-currency wallets for travellers. Its wallet keeps one `BigDecimal` balance, so a dollar refund was added to rupee cashback. Reconciliation compares amounts with `equals`, so ₹10.5 and ₹10.50 fail to match and land in a manual-review queue.

## Acceptance criteria

1.  **Given** credits of "10.5" and "10.50" INR, **then** both show as 10.50 and the balance is 21.00.
2.  **Given** ₹100 and \$5 credited, **then** the balance shows 100.00 INR and 5.00 USD, separately.
3.  **Given** "1500" JPY, **then** 1500 with no decimals; "1500.5" JPY or "10.505" INR is `422`.
4.  **Given** an unsupported currency or a zero amount, **then** `422`; a negative or malformed amount, `400`.
5.  **Given** an unknown wallet, **then** `404`.
6.  **Given** two `Money` values, **then** they are equal exactly when the currency and the minor units are equal.

## Requirements

- Amounts arrive as decimal strings; up to 999,999 per credit (a demo rule). Currency codes are normalised with `Locale.ROOT`.
- Money is stored as whole minor units with its `Currency`; conversion to minor units never rounds.
- Adding different currencies throws; overflow throws instead of wrapping around.
- Supported currencies (a demo set): INR, USD, AED, JPY.

## Learning objectives

- Write a value object as a record: immutable, compared by value.
- Explain `BigDecimal` scale, and why `equals` and `compareTo` disagree.
- Use `Currency.getDefaultFractionDigits` instead of assuming two decimals.
- Make the wrong operation (rupees plus dollars) impossible to do quietly.

# 2 · Build: API contract

## Endpoints

| Method | Path                    | Purpose                                                                               |
|--------|-------------------------|---------------------------------------------------------------------------------------|
| `POST` | `/wallets/{id}/credits` | Add an amount in one currency. `201` with the credit and that currency's new balance. |
| `GET`  | `/wallets/{id}/balance` | One balance per currency.                                                             |

## Request body

| Field       | Rule                                                                                                                                          |
|-------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| `amount`    | A string like `"10.50"`: digits, optionally a point and up to 4 decimals; at most 999999. The currency decides how many decimals are allowed. |
| `currency`  | Three letters, any case: INR, USD, AED or JPY.                                                                                                |
| `reference` | 1 to 40 characters, echoed back.                                                                                                              |

## Money in responses

`{"amount": "10.50", "currency": "INR", "minorUnits": 1050}`: the amount as a string with the currency's decimals, and the exact integer for machines.

## Status codes

| Status | When                                                                           |
|--------|--------------------------------------------------------------------------------|
| 201    | Credited                                                                       |
| 200    | Balance                                                                        |
| 400    | A field is missing or malformed (negative, exponent, too large, not 3 letters) |
| 404    | No such wallet                                                                 |
| 422    | Unsupported currency, more decimals than the currency has, or zero             |

## Captured examples

Captured with curl from the running app on 14 Oct 2026, in this order, on a fresh start. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: ₹10.5

**Why:** stored as 1,050 paise and shown with INR's two decimals: 10.50.

Request

``` code
POST /wallets/w-asha/credits HTTP/1.1
Content-Type: application/json

{
  "amount": "10.5",
  "currency": "INR",
  "reference": "cashback-1"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 175

{
  "walletId": "w-asha",
  "reference": "cashback-1",
  "credited": {
    "amount": "10.50",
    "currency": "INR",
    "minorUnits": 1050
  },
  "balance": {
    "amount": "10.50",
    "currency": "INR",
    "minorUnits": 1050
  }
}
```

### Case 2: ₹10.50

**Why:** the same Money as case 1; the balance is 21.00.

Request

``` code
POST /wallets/w-asha/credits HTTP/1.1
Content-Type: application/json

{
  "amount": "10.50",
  "currency": "INR",
  "reference": "cashback-2"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 175

{
  "walletId": "w-asha",
  "reference": "cashback-2",
  "credited": {
    "amount": "10.50",
    "currency": "INR",
    "minorUnits": 1050
  },
  "balance": {
    "amount": "21.00",
    "currency": "INR",
    "minorUnits": 2100
  }
}
```

### Case 3: \$5

**Why:** a new pocket. The INR balance is untouched.

Request

``` code
POST /wallets/w-asha/credits HTTP/1.1
Content-Type: application/json

{
  "amount": "5",
  "currency": "USD",
  "reference": "refund-us-store"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 176

{
  "walletId": "w-asha",
  "reference": "refund-us-store",
  "credited": {
    "amount": "5.00",
    "currency": "USD",
    "minorUnits": 500
  },
  "balance": {
    "amount": "5.00",
    "currency": "USD",
    "minorUnits": 500
  }
}
```

### Case 4: ¥1,500

**Why:** JPY has no minor unit, so 1,500 minor units is ¥1,500 and there is no ".00".

Request

``` code
POST /wallets/w-asha/credits HTTP/1.1
Content-Type: application/json

{
  "amount": "1500",
  "currency": "JPY",
  "reference": "trip-leftover"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 176

{
  "walletId": "w-asha",
  "reference": "trip-leftover",
  "credited": {
    "amount": "1500",
    "currency": "JPY",
    "minorUnits": 1500
  },
  "balance": {
    "amount": "1500",
    "currency": "JPY",
    "minorUnits": 1500
  }
}
```

### Case 5: the balance

**Why:** three balances, sorted by code, never added together.

Request

``` code
GET /wallets/w-asha/balance HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 193

{
  "walletId": "w-asha",
  "balances": [
    {
      "amount": "21.00",
      "currency": "INR",
      "minorUnits": 2100
    },
    {
      "amount": "1500",
      "currency": "JPY",
      "minorUnits": 1500
    },
    {
      "amount": "5.00",
      "currency": "USD",
      "minorUnits": 500
    }
  ]
}
```

### Case 6: ¥1,500.5

**Why:** half a yen cannot be stored: `422` instead of rounding it away.

Request

``` code
POST /wallets/w-asha/credits HTTP/1.1
Content-Type: application/json

{
  "amount": "1500.5",
  "currency": "JPY",
  "reference": "oops"
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "JPY amounts have 0 decimal places; 1500.5 has more.",
  "instance": "/wallets/w-asha/credits",
  "status": 422,
  "title": "Too many decimal places"
}
```

### Case 7: BTC

**Why:** not a currency this wallet holds: `422`.

Request

``` code
POST /wallets/w-asha/credits HTTP/1.1
Content-Type: application/json

{
  "amount": "5",
  "currency": "BTC",
  "reference": "oops"
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "This wallet holds AED, INR, JPY, USD, not BTC.",
  "instance": "/wallets/w-asha/credits",
  "status": 422,
  "title": "Currency not supported"
}
```

### Case 8: an unknown wallet

**Why:** `404`.

Request

``` code
GET /wallets/w-nobody/balance HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No wallet has the id w-nobody.",
  "instance": "/wallets/w-nobody/balance",
  "status": 404,
  "title": "Wallet not found"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                   | What happens                                  | Proved by                                      |
|--------------------------------------------------------|-----------------------------------------------|------------------------------------------------|
| 10.5 and 10.50 INR                                     | Equal, same hash code                         | `equalAmountsAreEqualWhateverTheTrailingZeros` |
| ₹100 + \$5 in code                                     | `CurrencyMismatchException`                   | `addingDifferentCurrenciesIsRefused`           |
| a + b                                                  | A new value; a and b unchanged                | `plusReturnsANewValueAndChangesNeither`        |
| ¥1,500; ₹0.1; ₹0.105; ¥1.5                             | 1500 JPY; 0.10 INR; refused; refused          | `decimalsFollowTheCurrency`                    |
| Long.MAX_VALUE + 1                                     | `ArithmeticException`, not a negative balance | `overflowIsAnErrorNotAWrapAround`              |
| "10.5" then "10.50" via HTTP; mixed-case ids and codes | 21.00; normalised                             | `aCreditIsShownInTheCurrencysOwnDecimals`      |
| JPY with decimals; INR with 3 decimals; "1500.00" JPY  | `422`, `422`, accepted                        | `yenHaveNoDecimals`                            |
| No credits yet                                         | Empty list                                    | `anEmptyWalletHasNoBalances`                   |
| BTC; 0.00; -5; 1e3; 1000000; RUPEES; empty body        | `422` or `400`                                | `badCreditsAreRefused`                         |
| Unknown wallet                                         | `404`                                         | `anUnknownWalletIs404`                         |

## The trap

Plausible but wrong

Adding amounts in different currencies, or comparing `BigDecimal` with `equals`.

The first test shows the old wallet's balance of 105 after ₹100 and \$5. The second shows `equals` calling 10.5 and 10.50 different, and a `HashSet` keeping both, while two `Money` values are one. The third shows the wallet keeping separate balances. While building, removing the currency check turned a test red, and so did rounding instead of refusing extra decimals. Keying every balance under INR made the `Money` type itself refuse the addition: the type caught a bug in the code around it.

``` code
package com.tijori.wallets;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.Currency;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/** The first test written for this station: it reproduces the bugs before the fix. */
class RupeesPlusDollarsTrapTest extends ApiTest {

    static final Currency INR = Currency.getInstance("INR");

    /** The "before" wallet: one BigDecimal balance, whatever the currency. Kept only in tests. */
    static BigDecimal oldBalanceAfter(String... amounts) {
        BigDecimal balance = BigDecimal.ZERO;
        for (String a : amounts) {
            balance = balance.add(new BigDecimal(a));
        }
        return balance;
    }

    @Test
    void theOldWalletAddsRupeesToDollars() {
        // Rs 100 and then USD 5: the old balance says "105" of nothing in particular.
        assertThat(oldBalanceAfter("100", "5")).isEqualByComparingTo("105");
    }

    @Test
    void bigDecimalEqualsSeesTenPointFiveAndTenPointFiftyAsDifferent() {
        assertThat(new BigDecimal("10.5").equals(new BigDecimal("10.50"))).isFalse();     // equals compares scale too
        assertThat(new BigDecimal("10.5").compareTo(new BigDecimal("10.50"))).isZero();   // compareTo compares value
        Set<BigDecimal> credits = new HashSet<>(List.of(new BigDecimal("10.5"), new BigDecimal("10.50")));
        assertThat(credits).hasSize(2);   // "two different amounts" in a set, a map key or a duplicate check

        assertThat(Money.parse("10.5", INR)).isEqualTo(Money.parse("10.50", INR));
        assertThat(new HashSet<>(List.of(Money.parse("10.5", INR), Money.parse("10.50", INR)))).hasSize(1);
    }

    @Test
    void theWalletKeepsOneBalancePerCurrency() throws Exception {
        credit("w-asha", "100", "INR");
        credit("w-asha", "5", "USD");
        balance("w-asha")
                .andExpect(jsonPath("$.balances", hasSize(2)))
                .andExpect(jsonPath("$.balances[0].amount").value("100.00"))
                .andExpect(jsonPath("$.balances[0].currency").value("INR"))
                .andExpect(jsonPath("$.balances[1].amount").value("5.00"))
                .andExpect(jsonPath("$.balances[1].currency").value("USD"));
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

The body is in `docs/credit.json`. Send it twice, once with `"10.5"`, and compare.

``` code
# Credit: expect credited.amount "10.50" and minorUnits 1050
curl -i -X POST http://localhost:8080/wallets/w-asha/credits -H "Content-Type: application/json" -d "@docs/credit.json"

# Balances, one per currency
curl http://localhost:8080/wallets/w-asha/balance
```

## Troubleshooting

| You see                            | Cause                                           | Fix                                                      |
|------------------------------------|-------------------------------------------------|----------------------------------------------------------|
| `404`                              | Only `w-asha` and `w-ravi` exist.               | Use one of them.                                         |
| `422` Too many decimal places      | The currency has fewer decimals (JPY has none). | Send the amount in that currency's decimals.             |
| `release version 25 not supported` | Maven is using an older JDK.                    | Point `JAVA_HOME` at JDK 25, or add `-Djava.version=21`. |

## Project layout

``` tree
stations/019-a-money-type-for-a-multi-currency-wallet/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tijori/wallets/
│   ├── WalletController.java   ├── Money.java   └── WalletsApplication.java
├── src/test/java/com/tijori/wallets/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/tijori/wallets/WalletController.java`

Does  
Validates the request, checks the currency, parses the amount into Money, and adds it to that currency's balance.

Why  
`ConcurrentHashMap.merge` with `Money::plus`: atomic per currency, and the type does the arithmetic.

Without it  
One `BigDecimal` balance per wallet.

#### `src/main/java/com/tijori/wallets/Money.java`

Does  
The value object: minor units and a currency.

Why  
A record gives value equality for free; the compact constructor and methods keep it correct.

Without it  
The trap: amounts without currencies, compared with `equals`.

- `setScale(digits)` with no rounding mode throws if a digit would be lost.
- `plus` checks the currency and uses `Math.addExact`.
- `amount()` formats with the currency's own decimals.

#### `src/main/resources/application.yaml`

Problem bodies for every error.

#### `src/main/java/com/tijori/wallets/WalletsApplication.java`

Standard Spring Boot entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                                   | Test class                      | Result |
|---------------|-------------------------------------------------------------------------------|---------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                                      | `WalletContractTest` (5)        | pass   |
| Every station | Reproduce the failure before the fix                                          | `RupeesPlusDollarsTrapTest` (3) | pass   |
| This station  | The value object: equality, currency safety, immutability, decimals, overflow | `MoneyTest` (5)                 | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.wallets.WalletContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.wallets.RupeesPlusDollarsTrapTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.wallets.MoneyTest
[INFO] Tests run: 13, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/tijori/wallets/RupeesPlusDollarsTrapTest.java`

Written first: the old balance of 105, `equals` versus `compareTo`, and separate balances.

#### `src/test/java/com/tijori/wallets/WalletContractTest.java`

Credits in each currency's decimals, an empty wallet, and every refusal.

#### `src/test/java/com/tijori/wallets/MoneyTest.java`

The value object with no Spring at all.

#### `src/test/java/com/tijori/wallets/ApiTest.java`

Shared setup: the whole app through MockMvc, every wallet empty before each test.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/tijori/wallets/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=DebitChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 13 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 17 tests pass (13 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Debits

Add `POST /wallets/{id}/debits` with the same body. Take the amount from that currency's balance, never below zero; `422` otherwise.

**Done when:** both tests in `DebitChallengeTest` pass.

Hints

- Add `minus` to `Money` by reusing `plus`; the currency check comes for free.
- `ConcurrentHashMap.compute` is atomic per key, and throwing inside it leaves the balance unchanged.

#### `challenge/DebitChallengeTest.java`

``` code
package com.tijori.wallets;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: POST /wallets/{id}/debits takes money out of one currency's balance, never below zero. */
class DebitChallengeTest extends ApiTest {

    ResultActions debit(String amount, String currency) throws Exception {
        return mvc.perform(post("/wallets/w-asha/debits").contentType(MediaType.APPLICATION_JSON).content(
                "{\"amount\":\"" + amount + "\",\"currency\":\"" + currency + "\",\"reference\":\"test\"}"));
    }

    @Test
    void aDebitLowersThatCurrencysBalance() throws Exception {
        credit("w-asha", "100", "INR");
        debit("40.5", "INR")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.debited.amount").value("40.50"))
                .andExpect(jsonPath("$.balance.amount").value("59.50"));
    }

    @Test
    void moreThanTheBalanceOrAnotherCurrencyIsRefused() throws Exception {
        credit("w-asha", "100", "INR");
        debit("100.01", "INR").andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.title").value("Insufficient balance"));
        debit("1", "USD").andExpect(status().isUnprocessableContent());   // rupees do not pay for dollars
        debit("100", "INR").andExpect(jsonPath("$.balance.amount").value("0.00"));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## An indicative total

Add `?in=USD` to the balance: an `indicativeTotal` converting each balance at demo rates (in rupees: INR 1, USD 88.00, AED 24.00, JPY 0.60), each rounded half-even to the target's decimals, then added.

**Done when:** both tests in `IndicativeTotalChallengeTest` pass: 16.37 USD, 1440.00 INR, 2400 JPY for the same wallet.

Hints

- Convert through rupees: amount × rate of its currency ÷ rate of the target.
- Round each converted balance once, then add them as `Money` in the target currency.

#### `challenge/IndicativeTotalChallengeTest.java`

``` code
package com.tijori.wallets;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /wallets/{id}/balance?in=USD adds an indicativeTotal, converting each balance with demo rates
 * (INR 1, USD 88.00, AED 24.00, JPY 0.60, all in rupees) and rounding each one half-even to the target's decimals.
 */
class IndicativeTotalChallengeTest extends ApiTest {

    @Test
    void balancesAreConvertedOneByOneThenAdded() throws Exception {
        credit("w-asha", "100", "INR");
        credit("w-asha", "5", "USD");
        credit("w-asha", "1500", "JPY");
        mvc.perform(get("/wallets/w-asha/balance").param("in", "INR"))
                .andExpect(jsonPath("$.indicativeTotal.amount").value("1440.00"));
        mvc.perform(get("/wallets/w-asha/balance").param("in", "usd"))
                .andExpect(jsonPath("$.indicativeTotal.amount").value("16.37"))      // 1.14 + 5.00 + 10.23
                .andExpect(jsonPath("$.indicativeTotal.currency").value("USD"));
        mvc.perform(get("/wallets/w-asha/balance").param("in", "JPY"))
                .andExpect(jsonPath("$.indicativeTotal.amount").value("2400"));      // 167 + 733 + 1500
    }

    @Test
    void withoutInThereIsNoTotalAndAnUnsupportedCurrencyIs422() throws Exception {
        credit("w-asha", "100", "INR");
        mvc.perform(get("/wallets/w-asha/balance")).andExpect(jsonPath("$.indicativeTotal").doesNotExist());
        mvc.perform(get("/wallets/w-asha/balance").param("in", "BTC")).andExpect(status().isUnprocessableContent());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Money in a database

How would you store `Money` in PostgreSQL: a `bigint` of minor units and a `char(3)` currency, or a `numeric`? What constraint stops a JPY row from holding a fraction, and what happens if ISO 4217 changes a currency's minor unit?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the old balance of 105, and `equals` on 10.5 and 10.50.
2.  Write `Money` as a record of minor units and a currency; test it without Spring.
3.  Parse amounts with the currency's decimals, refusing any loss.
4.  Keep one balance per currency in the wallet.

## Design alternatives and trade-offs

| Approach                                           | What it costs                                                                      | Verdict      |
|----------------------------------------------------|------------------------------------------------------------------------------------|--------------|
| Minor units (`long`) + `Currency`                  | A conversion at the edges.                                                         | Chosen       |
| `BigDecimal` + currency, compared with `compareTo` | Works, but every map, set and `equals` must remember to normalise the scale first. | Error-prone  |
| `BigDecimal` with `stripTrailingZeros`             | 10 becomes 1E+1; formatting and equality get surprising.                           | Avoid        |
| `double`                                           | 0.1 + 0.2 is not 0.3.                                                              | Wrong        |
| A money library (for example JSR 354 / Moneta)     | Another dependency; worth it with many currencies and conversions.                 | Later, maybe |

## Database design

None in this station. With a database: `wallet_balances` (wallet_id, currency `char(3)`, minor_units `bigint`) with a primary key on (wallet_id, currency) and a check that minor_units is not negative. The currency's decimals stay in code, from ISO 4217.

# 3 · Go deeper: Production

Regulation  
Holding foreign currency for customers in India is regulated. This station shows the data model only.

JSON  
Amounts travel as strings, with the integer minor units alongside. A client that parses JSON numbers as floating point cannot damage a string.

Concurrency  
`merge` on a `ConcurrentHashMap` is atomic per key, so two credits at once both count. A database would need the same guarantee from a row lock or an atomic update.

Display  
Show the currency with every amount. Formatting for a locale (₹1,00,000.00 or \$100,000.00) belongs in the client.

# 3 · Go deeper: Interview

## Interview takeaways

Why are new BigDecimal("10.5") and new BigDecimal("10.50") not equal?

equals compares the unscaled value and the scale: 105 with scale 1 versus 1050 with scale 2. compareTo compares only the value, so it returns 0. HashMap and HashSet use equals and hashCode, so they keep both.

What makes a good value object?

Immutable, compared by its values, valid from construction, and with operations that return new values. A Java record gives the first two for free.

Why store minor units as a long?

Integers are exact, fast and compare simply. The currency says where the decimal point goes. A long holds more than any wallet needs; addExact turns an overflow into an error.

How do you stop rupees being added to dollars?

Make Money carry its currency and make plus refuse a different one. The mistake then fails loudly at the first test, not in a customer's balance.

Are all currencies two decimals?

No. ISO 4217 gives each currency's minor unit: JPY has none, some have three. java.util.Currency.getDefaultFractionDigits returns it.

## Self-check rubric

| Area          | Meets the bar                          | Above the bar                                       |
|---------------|----------------------------------------|-----------------------------------------------------|
| Correctness   | All 13 tests pass.                     | You can explain each refusal in the contract test.  |
| Value objects | Money is immutable and equal by value. | You know what a record does and does not give you.  |
| BigDecimal    | `equals` versus `compareTo`.           | Why `setScale` without rounding throws.             |
| Explanation   | Why amounts carry their currency.      | Minor units versus BigDecimal, with the trade-offs. |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any money code:

- Does every amount travel with its currency?
- Is any `BigDecimal` compared with `equals`, or used as a map key?
- Does any code assume two decimals?
- Can an addition overflow, and what happens if it does?
