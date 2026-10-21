# Station 078 · Customers see only their own accounts

Working Systems · 0–2 years · Core · Fintech · Types: Database, Security

Spring Boot 4.1.1 · Java 25 · Spring Security 7 (HTTP Basic, JDBC users) · authorisation in SQL · JdbcClient · PostgreSQL 17 · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Customers, accounts and statement lines are demo rows, not Tijori's; no bank is involved. Balances are numbers in a table: nothing is paid or transferred.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 16 tests.

# 1 · Understand

## The problem in real life

1.  **A number in the URL**

    Tijori's statement page opened `/accounts/1001/statements`. Account numbers count up.

2.  **The next number**

    A customer changed 1001 to 1002 and saw another customer's statement. The server had looked the account up by its number alone.

3.  **The fix**

    Every query names the signed-in customer as well as the account. Someone else's account finds no row, and gets the same 404 as a number that does not exist.

An id in a URL is a request, not a right. Ask whose it is in the same query that fetches it.

## What are we building?

`GET /accounts/{id}` and `GET /accounts/{id}/statements?month=` that return a row only to its holders.

## An everyday analogy

A bank teller who reads out a balance only after checking the customer's name is on that account, and who says "no such account" both for numbers that do not exist and for numbers that are not yours.

## How it works in 4 steps

1.  **Sign in**: email and password with every request.
2.  **Ask**: the URL names an account.
3.  **Query**: account, holders and customer joined; the signed-in email is in the WHERE clause.
4.  **Answer**: no row is 404; a holder without statement rights is 403; otherwise the data.

Check yourself: why 404 and not 403 for someone else's account?

A 403 says the account exists. Walking through the numbers would then map every account. With 404 for both, the numbers reveal nothing: `walkingThroughTheNumbersFindsOnlyYourOwn`.

## What this station is not

- **No payments.** Statement lines are demo rows.
- **No list of accounts.** Practice, challenge 1 adds it.
- **No staff access.** Bank staff viewing accounts is Practice, challenge 3.

## Key terms

| Term                           | Simple meaning                                                                                            | Everyday example                                                                | In this project                |
|--------------------------------|-----------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|--------------------------------|
| **IDOR**                       | Insecure direct object reference: the server returns whatever id you ask for, without asking whose it is. | A cloakroom that hands over any coat for any ticket number you say.             | the old statement page         |
| **Ownership check**            | Is this signed-in person allowed this record?                                                             | The cloakroom checks the ticket is yours.                                       | `account_holders`              |
| **Authorisation in the query** | The WHERE clause names both the record and the person, so a stranger's request finds no row.              | Looking in your own locker, not checking each locker's name tag.                | `JOIN ... c.email = ?`         |
| **404 or 403**                 | 404: no such thing (for you). 403: it exists, and you may not do this.                                    | "No coat under that number" against "that coat is yours, but not the umbrella". | stranger 404, balance-only 403 |
| **Joint account**              | One account, several holders.                                                                             | A shared locker.                                                                | account 1003                   |
| **Paise**                      | Money as whole paise, never fractions of a rupee in a floating point.                                     | Counting coins, not weighing them.                                              | `balance_paise`                |

# 2 · Build: Spec

## Business problem

**Tijori** (a fictional bank): changing the account id in the URL showed another customer's statement.

## Acceptance criteria

Demo data: Zoya holds 1001 and the joint 1003; Dev holds 1002, 1003 and the shop's 1004; Ravi, the shop assistant, may see 1004's balance only.

1.  **Given** a holder, **then** the account and its balance.
2.  **Given** a full holder and a month, **then** that month's lines with opening and closing balances that add up.
3.  **Given** an account that is not the caller's, or does not exist, **then** the same `404`.
4.  **Given** a balance-only holder asking for statements, **then** `403`.
5.  **Given** a holder removed from a joint account, **then** `404` on the next request.
6.  **Given** an id or month that is not one, **then** `400`.

## Requirements

- Every query that reads an account names the signed-in customer.
- Answers never tell an outsider whether an account number exists.
- Money is integer paise.

## Learning objectives

- Recognise IDOR and fix it in the query, not in a later check.
- Choose 404 or 403 on purpose.
- Model joint holders and partial access in tables.
- Test by walking through ids as an attacker would.

# 2 · Build: API contract

## Endpoints

| Method | Path                                      | Purpose                                                                             |
|--------|-------------------------------------------|-------------------------------------------------------------------------------------|
| `GET`  | `/accounts/{id}`                          | Kind, name, balance in paise, and this sign-in's access (`full` or `balance_only`). |
| `GET`  | `/accounts/{id}/statements?month=YYYY-MM` | That month's lines, oldest first, with opening and closing balances.                |

## Status codes

| Status | When                                                             |
|--------|------------------------------------------------------------------|
| 200    | The account or statement, for a holder                           |
| 400    | An id that is not a number; a month that is not `YYYY-MM`        |
| 401    | No or wrong credentials                                          |
| 403    | A balance-only holder asking for statements; a path with no rule |
| 404    | Not the caller's account, or no such account: the same answer    |

## Captured examples

Captured with curl from the running app on 21 Oct 2026. JSON bodies are indented for reading; `Date`, connection and standard security headers are left out.

### Case 1: Zoya's own account

**Why:** she is a full holder.

Request

``` code
GET /accounts/1001 HTTP/1.1
Authorization: Basic em95YUBleGFtcGxlLmNvbTp6b3lhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 86

{
  "id": 1001,
  "kind": "savings",
  "name": "Zoya Khan",
  "balancePaise": 9850000,
  "access": "full"
}
```

### Case 2: the next number, 1002

**Why:** Dev's: `404`.

Request

``` code
GET /accounts/1002 HTTP/1.1
Authorization: Basic em95YUBleGFtcGxlLmNvbTp6b3lhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No such account",
  "instance": "/accounts/1002",
  "status": 404,
  "title": "Not Found"
}
```

### Case 3: a number that does not exist

**Why:** the same `404` as case 2, word for word.

Request

``` code
GET /accounts/9999 HTTP/1.1
Authorization: Basic em95YUBleGFtcGxlLmNvbTp6b3lhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No such account",
  "instance": "/accounts/9999",
  "status": 404,
  "title": "Not Found"
}
```

### Case 4: Zoya's September statement

**Why:** opening plus the lines is the closing balance; October's bill is after it.

Request

``` code
GET /accounts/1001/statements?month=2026-09 HTTP/1.1
Authorization: Basic em95YUBleGFtcGxlLmNvbTp6b3lhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 356

{
  "accountId": 1001,
  "month": "2026-09",
  "openingBalancePaise": 3945000,
  "closingBalancePaise": 10095000,
  "lines": [
    {
      "bookedOn": "2026-09-01",
      "description": "Salary, Acme Analytics",
      "amountPaise": 9500000
    },
    {
      "bookedOn": "2026-09-05",
      "description": "Rent, September",
      "amountPaise": -3200000
    },
    {
      "bookedOn": "2026-09-18",
      "description": "UPI to Dev Patel",
      "amountPaise": -150000
    }
  ]
}
```

### Case 5: the joint account, as Dev

**Why:** both holders see it.

Request

``` code
GET /accounts/1003 HTTP/1.1
Authorization: Basic ZGV2QGV4YW1wbGUuY29tOmRldi1kZW1vLXBhc3M=
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 100

{
  "id": 1003,
  "kind": "savings",
  "name": "Zoya Khan and Dev Patel",
  "balancePaise": 7500000,
  "access": "full"
}
```

### Case 6: the shop's account, as Ravi

**Why:** balance only, and the answer says so.

Request

``` code
GET /accounts/1004 HTTP/1.1
Authorization: Basic cmF2aUBleGFtcGxlLmNvbTpyYXZpLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 105

{
  "id": 1004,
  "kind": "current",
  "name": "Patel Kirana Stores",
  "balancePaise": 32012575,
  "access": "balance_only"
}
```

### Case 7: the shop's statement, as Ravi

**Why:** `403`: a holder, without the right to statements.

Request

``` code
GET /accounts/1004/statements?month=2026-09 HTTP/1.1
Authorization: Basic cmF2aUBleGFtcGxlLmNvbTpyYXZpLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 403 
Content-Type: application/problem+json

{
  "detail": "This sign-in may see the balance only",
  "instance": "/accounts/1004/statements",
  "status": 403,
  "title": "Forbidden"
}
```

### Case 8: month 2026-13

**Why:** `400`.

Request

``` code
GET /accounts/1001/statements?month=2026-13 HTTP/1.1
Authorization: Basic em95YUBleGFtcGxlLmNvbTp6b3lhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Validation failure",
  "instance": "/accounts/1001/statements",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 9: no credentials

**Why:** `401` with a Basic challenge.

Request

``` code
GET /accounts/1001 HTTP/1.1
```

Response

``` code
HTTP/1.1 401 
WWW-Authenticate: Basic realm="tijori"
Content-Type: application/problem+json
Content-Length: 113

{
  "title": "Sign-in required",
  "status": 401,
  "detail": "Send a valid email and password.",
  "instance": "/accounts/1001"
}
```

## Who holds what

From `psql` in `docs/capture.sh`.

``` code
 account_id |      email       |    access    
------------+------------------+--------------
       1001 | zoya@example.com | full
       1002 | dev@example.com  | full
       1003 | dev@example.com  | full
       1003 | zoya@example.com | full
       1004 | dev@example.com  | full
       1004 | ravi@example.com | balance_only
(6 rows)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                        | What happens                      | Proved by                                                   |
|-------------------------------------------------------------|-----------------------------------|-------------------------------------------------------------|
| Own account                                                 | `200`                             | `aCustomerSeesTheirAccount`                                 |
| A month's statement                                         | Lines in order; balances add up   | `aMonthsStatementHasItsLinesAndBalancesThatAddUp`           |
| A joint account                                             | Both holders                      | `bothHoldersOfAJointAccountSeeIt`                           |
| A month with no lines                                       | Empty, opening equals closing     | `aMonthWithNoLinesIsEmptyNotAnError`                        |
| Unknown account; bad id or month                            | `404`; `400`                      | `unknownAccountsAre404AndBadParametersAre400`               |
| No, wrong or unknown credentials                            | `401`                             | `noOrWrongCredentialsAre401`                                |
| Balance-only holder; a stranger                             | `403` for statements; `404`       | `aBalanceOnlyHolderGets403ForStatementsAndAStrangerGets404` |
| A joint holder removed                                      | `404` on the next request         | `removingAJointHolderTakesEffectOnTheNextRequest`           |
| SQL-looking, negative, huge, encoded ids; an injected month | `400` or `404`, never an error    | `oddIdsAndMonthsAre400Or404NeverAnError`                    |
| Writes and unknown paths                                    | `403`                             | `writesAndOtherPathsAreRefused`                             |
| Rules written by plain SQL                                  | Refused by named constraints      | `accountRulesHoldWithoutJava`                               |
| A debit that would overdraw                                 | Line and balance both rolled back | `aDebitThatWouldOverdrawLeavesNeitherLineNorBalance`        |
| The current month                                           | Closes at the current balance     | `theNewestStatementClosesAtTheCurrentBalance`               |

## The trap

Plausible but wrong

Trusting the id in the URL without an ownership check (IDOR).

- **The next number.** The old query returns Dev's account 1002 to Zoya. The API: `404`, for the account and its statements.
- **Walking the numbers.** Zoya asks for 1000 to 1005. Only 1001 and 1003 answer; the others, Dev's and the ones that do not exist, look the same.
- **The control.** Her own account and statement work.

While building, each part was undone once: trusting the id (the customer join made always true) turned 4 tests red; no balance-only check 1; `denyAll` replaced by `authenticated` 1. Two changes turned nothing red, explained in the Code tab.

``` code
package com.tijori.accounts;

import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old statement page looked the account up by the id in the URL, and nothing else. Account
 * numbers count up, so changing 1001 to 1002 showed the next customer's statement. Each test runs the old query,
 * then asks the API the same question as the same customer.
 */
class UrlIdTrustTrapTest extends ApiTest {

    /** The old lookup, as it was: trust the id. */
    Map<String, Object> oldLookup(long accountId) {
        return jdbc.sql("SELECT id, name, balance_paise FROM accounts WHERE id = ?").param(accountId).query().singleRow();
    }

    @Test
    void changingTheIdInTheUrlShowedTheNextCustomersAccount() throws Exception {
        assertThat(oldLookup(1002)).containsEntry("name", "Dev Patel");   // zoya, signed in, asking for 1002
        account("zoya", 1002).andExpect(status().isNotFound());
        statement("zoya", 1002, "2026-09").andExpect(status().isNotFound());
    }

    @Test
    void walkingThroughTheNumbersFindsOnlyYourOwn() throws Exception {
        // Not someone else's and not existing look the same: the numbers reveal nothing.
        for (long id = 1000; id <= 1005; id++) {
            int s = account("zoya", id).andReturn().getResponse().getStatus();
            assertThat(s).as("account %d", id).isEqualTo(id == 1001 || id == 1003 ? 200 : 404);
        }
    }

    @Test
    void theOwnAccountStillWorks() throws Exception {
        // The control.
        account("zoya", 1001).andExpect(status().isOk());
        statement("zoya", 1001, "2026-09").andExpect(status().isOk());
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
docker compose up -d        # PostgreSQL 17 on localhost:5432
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 16 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Walk through the account numbers as Zoya, as an attacker would:

``` code
for id in 1000 1001 1002 1003 1004 1005; do
  curl -s -o /dev/null -w "$id %{http_code}\n" -u zoya@example.com:zoya-demo-pass http://localhost:8080/accounts/$id
done
```

Only 1001 and 1003 print 200. 1002 and 1004 exist, but print the same 404 as 1000 and 1005.

## Troubleshooting

| You see                                     | Cause                                                              | Fix                                                                         |
|---------------------------------------------|--------------------------------------------------------------------|-----------------------------------------------------------------------------|
| `403` for someone else's account            | The ownership check runs after the lookup and answers "forbidden". | Put the customer into the query, and answer 404.                            |
| A statement whose balances do not add up    | Lines and balance read at different moments.                       | Read them in one REPEATABLE READ transaction, as `Accounts.statement` does. |
| `Could not find a valid Docker environment` | Docker is not running.                                             | Start Docker Desktop or the Docker service.                                 |

## Project layout

``` tree
stations/078-customers-see-only-their-own-accounts/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/tijori/accounts/
│   ├── SecurityConfig.java   ├── AccountController.java   ├── Accounts.java
│   ├── ProblemResponses.java   └── AccountsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__customers_accounts_holders.sql, V2__demo_data.sql
├── src/test/java/com/tijori/accounts/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/tijori/accounts/SecurityConfig.java`

Does  
Sign-in against the customers table, and the two paths.

Why  
HTTP Basic, bcrypt, stateless; both paths need a sign-in; everything else refused. Which accounts is decided per query.

Without it  
Writes or new paths open to every signed-in customer.

#### `src/main/java/com/tijori/accounts/AccountController.java`

Does  
The two endpoints.

Why  
The customer comes from the sign-in, the account from the URL; the month is checked before it is parsed.

Without it  
A parameter choosing the customer, or a bad month turning into a 500.

#### `src/main/java/com/tijori/accounts/Accounts.java`

Does  
The ownership rule, inside the SQL.

Why  
The account query joins holders and customers on the signed-in email; no row is `404`; balance-only holders get `403` for statements; the statement reads in one REPEATABLE READ transaction.

Without it  
IDOR, and statements whose lines and balances disagree.

- The lines query repeats the ownership join. Removing it turned no test red, because `account()` already refused; it stays so the query is safe on its own if someone reuses it.
- No test proves the REPEATABLE READ: none makes a payment commit between the statement's queries. Under READ COMMITTED it could, and the opening balance would be wrong for that one request.

#### `src/main/java/com/tijori/accounts/ProblemResponses.java`

401 with a Basic challenge and 403 in the same problem JSON as every other error.

#### `src/main/resources/db/migration/V1__customers_accounts_holders.sql`

Does  
Customers, accounts, holders, statement lines.

Why  
A holder table with an access level; non-negative balances; non-zero lines.

Without it  
An account with no rule about who may see it.

#### `src/main/resources/db/migration/V2__demo_data.sql`

Three customers, four accounts (one joint, one shop), September 2026 lines.

#### `src/main/resources/application.yaml`

The database connection.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/tijori/accounts/AccountsApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                       | Test class                | Result |
|---------------|-------------------------------------------------------------------|---------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                          | `AccountContractTest` (5) | pass   |
| Every station | Reproduce the failure before the fix                              | `UrlIdTrustTrapTest` (3)  | pass   |
| Database      | Rollback and constraint tests against a real database             | `AccountDatabaseTest` (3) | pass   |
| Security      | 401, 403, one user accessing another user's data, malicious input | `AccountSecurityTest` (5) | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, Spring Security 7.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.accounts.AccountContractTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.accounts.AccountSecurityTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.accounts.UrlIdTrustTrapTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.accounts.AccountDatabaseTest
[INFO] Tests run: 16, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/tijori/accounts/UrlIdTrustTrapTest.java`

Written first: the old lookup by id, and the same requests to the API, including a walk through the numbers.

#### `src/test/java/com/tijori/accounts/AccountSecurityTest.java`

401, 404 against 403, a removed joint holder, odd ids and months, writes.

#### `src/test/java/com/tijori/accounts/AccountDatabaseTest.java`

Every named constraint with plain SQL; a debit that overdraws rolls back with its line.

#### `src/test/java/com/tijori/accounts/AccountContractTest.java`

Accounts and statements through HTTP, balances that add up.

#### `src/test/java/com/tijori/accounts/ApiTest.java`

Shared setup: request helpers with HTTP Basic.

#### `src/test/java/com/tijori/accounts/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/tijori/accounts/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=MyAccountsChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 16 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 19 tests pass (16 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 15 minutes

## My accounts

`GET /accounts` lists the signed-in customer's own accounts, by number, with this sign-in's access.

**Done when:** the test in `MyAccountsChallengeTest` passes.

Hints

- The same joins as the account query, without the account id.
- The filter chain needs a rule for the new path.

#### `challenge/MyAccountsChallengeTest.java`

``` code
package com.tijori.accounts;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: GET /accounts lists the signed-in customer's own accounts (id, name, access), by account number. */
class MyAccountsChallengeTest extends ApiTest {

    @Test
    void eachCustomerSeesOnlyTheirOwnList() throws Exception {
        mvc.perform(get("/accounts").with(httpBasic("zoya@example.com", "zoya-demo-pass"))).andExpect(status().isOk())
                .andExpect(jsonPath("$[*].id", contains(1001, 1003)));
        mvc.perform(get("/accounts").with(httpBasic("ravi@example.com", "ravi-demo-pass")))
                .andExpect(jsonPath("$[*].id", contains(1004))).andExpect(jsonPath("$[0].access").value("balance_only"));
        mvc.perform(get("/accounts")).andExpect(status().isUnauthorized());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 30 minutes

## Statement as CSV

`GET /accounts/{id}/statements.csv?month=`: the same rules as the JSON statement, amounts in rupees with two decimals, descriptions with a comma quoted, as a download.

**Done when:** both tests in `StatementCsvChallengeTest` pass.

Hints

- Call the same `statement` method: the rules come with it.
- `BigDecimal.valueOf(paise, 2).toPlainString()` turns paise into rupees without a double.

#### `challenge/StatementCsvChallengeTest.java`

``` code
package com.tijori.accounts;

import org.junit.jupiter.api.Test;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /accounts/{id}/statements.csv?month=2026-09 as a CSV download, with the same rules as the JSON
 * statement (404 for others' accounts, 403 for balance-only). Amounts in rupees from paise, two decimals, no
 * thousands separator; descriptions with a comma are quoted.
 */
class StatementCsvChallengeTest extends ApiTest {

    @Test
    void aMonthAsCsv() throws Exception {
        mvc.perform(get("/accounts/1001/statements.csv").param("month", "2026-09").with(httpBasic("zoya@example.com", "zoya-demo-pass")))
                .andExpect(status().isOk()).andExpect(header().string("Content-Type", "text/csv;charset=UTF-8"))
                .andExpect(header().string("Content-Disposition", "attachment; filename=\"tijori-1001-2026-09.csv\""))
                .andExpect(content().string("""
                        date,description,amount
                        2026-09-01,"Salary, Acme Analytics",95000.00
                        2026-09-05,"Rent, September",-32000.00
                        2026-09-18,UPI to Dev Patel,-1500.00
                        """));
    }

    @Test
    void theSameRulesAsTheJsonStatement() throws Exception {
        mvc.perform(get("/accounts/1002/statements.csv").param("month", "2026-09").with(httpBasic("zoya@example.com", "zoya-demo-pass"))).andExpect(status().isNotFound());
        mvc.perform(get("/accounts/1004/statements.csv").param("month", "2026-09").with(httpBasic("ravi@example.com", "ravi-demo-pass"))).andExpect(status().isForbidden());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## When bank staff need to look

A support agent must see a customer's statement to answer a complaint. Design it without opening every account to every agent: a ticket the customer agreed to, a time limit, read-only access, and an audit the customer can see. Which parts belong in the query, and which in a separate check?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the old lookup, and a walk through the numbers.
2.  Model holders with an access level.
3.  Join the signed-in customer into every account query.
4.  Decide 404 and 403 on purpose, and test both.

## Design alternatives and trade-offs

| Approach                                        | What it costs                                                                        | Verdict                            |
|-------------------------------------------------|--------------------------------------------------------------------------------------|------------------------------------|
| Customer in the WHERE clause; 404 for strangers | Every query must carry the customer.                                                 | Chosen                             |
| Look up by id only                              | IDOR: any number, any account.                                                       | The trap                           |
| Look up, then check, then 403                   | Safe for the data; tells outsiders which numbers exist.                              | Leaks existence                    |
| Random account ids (UUIDs) in URLs              | Harder to guess; still IDOR when one leaks.                                          | A second layer, never the only one |
| PostgreSQL row-level security                   | Rules in the database for every query; the app must set the customer per connection. | Strong; needs care with pooling    |

## Database design

| Object                                               | What                                                    | Why                                          |
|------------------------------------------------------|---------------------------------------------------------|----------------------------------------------|
| `account_holders`                                    | PK (account, customer), access `full` or `balance_only` | Joint accounts and partial access, as data.  |
| `accounts_balance_nonnegative`                       | CHECK                                                   | No writer can overdraw a savings account.    |
| `transactions_amount_nonzero`, `_description_length` | CHECKs                                                  | Every line moves something and can be shown. |
| `account_holders_by_customer`                        | Index                                                   | The ownership join stays fast.               |

**Transaction boundary:** a statement is one REPEATABLE READ read-only transaction. A line and its balance change are written in one transaction (the rollback test).

``` code
CREATE TABLE customers (
    id            bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT customers_pk PRIMARY KEY,
    email         text NOT NULL,
    name          text NOT NULL,
    password_hash text NOT NULL,
    CONSTRAINT customers_email_lower CHECK (email = lower(email)),
    CONSTRAINT customers_email_unique UNIQUE (email),
    CONSTRAINT customers_password_hash_shape CHECK (password_hash ~ '^\{bcrypt\}\$2[aby]\$(1[0-9]|2[0-9]|3[01])\$[./A-Za-z0-9]{53}$')
);

-- Account numbers count up, as at most banks: anyone can guess the next one. Guessing must get nobody anywhere.
CREATE TABLE accounts (
    id            bigint CONSTRAINT accounts_pk PRIMARY KEY,
    kind          text NOT NULL,
    name          text NOT NULL,
    balance_paise bigint NOT NULL,
    CONSTRAINT accounts_kind CHECK (kind IN ('savings', 'current')),
    CONSTRAINT accounts_balance_nonnegative CHECK (balance_paise >= 0)
);

-- Who may see which account. 'full': balance and statements. 'balance_only': the balance, nothing else
-- (a shop assistant checking the shop's account, say).
CREATE TABLE account_holders (
    account_id  bigint NOT NULL CONSTRAINT account_holders_account_fk REFERENCES accounts ON DELETE CASCADE,
    customer_id bigint NOT NULL CONSTRAINT account_holders_customer_fk REFERENCES customers ON DELETE CASCADE,
    access      text NOT NULL,
    CONSTRAINT account_holders_pk PRIMARY KEY (account_id, customer_id),
    CONSTRAINT account_holders_access CHECK (access IN ('full', 'balance_only'))
);
CREATE INDEX account_holders_by_customer ON account_holders (customer_id);

-- Statement lines. Credits positive, debits negative, in paise; written in the same transaction as the balance change.
CREATE TABLE transactions (
    id           bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT transactions_pk PRIMARY KEY,
    account_id   bigint NOT NULL CONSTRAINT transactions_account_fk REFERENCES accounts ON DELETE CASCADE,
    booked_on    date NOT NULL,
    description  text NOT NULL,
    amount_paise bigint NOT NULL,
    CONSTRAINT transactions_amount_nonzero CHECK (amount_paise <> 0),
    CONSTRAINT transactions_description_length CHECK (char_length(description) BETWEEN 1 AND 140)
);
CREATE INDEX transactions_by_account_date ON transactions (account_id, booked_on);
```

# 3 · Go deeper: Production

Every new query  
IDOR comes back with each new endpoint. A code review rule ("which customer does this query name?") and a test that walks ids for each endpoint keep it out.

Watching  
Many 404s for one customer across nearby numbers is someone walking ids: alert on it.

Logs  
Account numbers in logs are personal data; statement lines more so.

Standards  
OWASP's API Security Top 10 (2023 edition) lists this first, as Broken Object Level Authorization.

# 3 · Go deeper: Interview

## Interview takeaways

What is IDOR?

Returning a record because its id was asked for, without checking the caller may see it. The fix is an ownership condition in the same query.

404 or 403 for someone else's record?

404 when even its existence is private, as for bank accounts; 403 when the caller may know it exists but not do this, like a balance-only holder asking for statements.

Do random ids fix IDOR?

They make guessing harder, not access correct. Ids leak through links, logs and screenshots.

Why put the check in the query and not after it?

The query cannot return what it never selects. A check after it can be forgotten in one code path, and its answer tends to leak existence.

How do you test for IDOR?

Sign in as one user and ask for another's ids, and for ids that do not exist; the answers must match.

## Self-check rubric

| Area        | Meets the bar            | Above the bar                                          |
|-------------|--------------------------|--------------------------------------------------------|
| Correctness | All 16 tests pass.       | You ran the flawed version and explained each failure. |
| Ownership   | Customer in every query. | Joint and partial access as data.                      |
| Answers     | 404 for strangers.       | 403 only where existence may be known.                 |
| Money       | Paise as integers.       | Statements that add up, read consistently.             |

# 3 · Go deeper: Review

## The pull request

A teammate splits the account query into "two simple queries": find the account, then check the holder, with a clear 403 when it is someone else's. The lines query drops its joins, since "the holder was checked above". Read the file and list every problem before opening the findings.

#### `review/Accounts.java`

``` code
package com.tijori.accounts;

import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDate;
import java.time.YearMonth;
import java.util.List;

/** Accounts and statements for signed-in customers. */
@Service
class Accounts {

    record Account(long id, String kind, String name, long balancePaise, String access) {
    }

    record Line(LocalDate bookedOn, String description, long amountPaise) {
    }

    record Statement(long accountId, String month, long openingBalancePaise, long closingBalancePaise, List<Line> lines) {
    }

    private final JdbcClient jdbc;

    Accounts(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /** Find the account, then check the holder: one simple query each, and a clear 403 when it is someone else's. */
    Account account(String customer, long accountId) {
        Account account = jdbc.sql("SELECT id, kind, name, balance_paise, 'full' AS access FROM accounts WHERE id = ?")
                .param(accountId).query(Account.class).optional().orElseThrow(Accounts::notFound);
        boolean holder = jdbc.sql("SELECT EXISTS (SELECT 1 FROM account_holders h JOIN customers c ON c.id = h.customer_id WHERE h.account_id = ? AND c.email = ?)")
                .params(accountId, customer).query(Boolean.class).single();
        if (!holder) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "This account belongs to another customer");
        }
        return account;
    }

    /**
     * One month's lines with opening and closing balances. One REPEATABLE READ transaction, so a payment landing
     * between the queries cannot make the lines and the balances disagree.
     */
    @Transactional(readOnly = true, isolation = Isolation.REPEATABLE_READ)
    Statement statement(String customer, long accountId, YearMonth month) {
        Account account = account(customer, accountId);
        LocalDate from = month.atDay(1);
        LocalDate to = month.plusMonths(1).atDay(1);
        List<Line> lines = jdbc.sql("""
                        SELECT booked_on, description, amount_paise FROM transactions
                        WHERE account_id = ? AND booked_on >= ? AND booked_on < ?
                        ORDER BY booked_on, id""")   // the holder was checked above
                .params(accountId, from, to).query(Line.class).list();
        long after = jdbc.sql("SELECT coalesce(sum(amount_paise), 0) FROM transactions WHERE account_id = ? AND booked_on >= ?")
                .params(accountId, to).query(Long.class).single();
        long closing = account.balancePaise() - after;
        long opening = closing - lines.stream().mapToLong(Line::amountPaise).sum();
        return new Statement(accountId, month.toString(), opening, closing, lines);
    }

    static ResponseStatusException notFound() {
        return new ResponseStatusException(HttpStatus.NOT_FOUND, "No such account");
    }
}
```

## Findings

1403 "belongs to another customer"

The lookup by id, then a holder check, keeps the data safe but answers differently for numbers that exist: walking the numbers now maps every account. The answer itself confirms the account is someone else's.

**Test evidence:** `changingTheIdInTheUrlShowedTheNextCustomersAccount`, `walkingThroughTheNumbersFindsOnlyYourOwn` and `removingAJointHolderTakesEffectOnTheNextRequest` fail (they expect 404).

2Balance-only holders see statements

The access level is no longer read: the account query returns `'full'` for everyone, so the shop assistant reads every sale and every withdrawal.

**Test evidence:** `aBalanceOnlyHolderGets403ForStatementsAndAStrangerGets404` fails.

3The lines query trusts the id

It is safe today only because a check ran first. Reused anywhere else, it is the original IDOR.

**Test evidence:** No test fails on this alone: the check above it still runs. That is why it is a review finding.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class            | Fixed version | Flawed version |
|-----------------------|---------------|----------------|
| `AccountContractTest` | 5 / 5         | 5 / 5          |
| `AccountDatabaseTest` | 3 / 3         | 3 / 3          |
| `AccountSecurityTest` | 5 / 5         | 3 / 5          |
| `UrlIdTrustTrapTest`  | 3 / 3         | 1 / 3          |

No customer sees another's data in this version. It still fails review: it tells strangers which accounts exist, and it gives the shop assistant the statements.
