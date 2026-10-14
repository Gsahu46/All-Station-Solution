# Station 021 · Parsing a bank statement CSV

Foundations · 0–1 years · Core · Fintech · Types: none

Spring Boot 4.1.1 · Java 25 · Spring MVC · java.time formatters · checked exceptions · MockMvc. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The statement is parsed and the result returned; nothing is stored and no bank is contacted. Sample files are made up.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 11 tests.

# 1 · Understand

## The problem in real life

1.  **Meera uploads a year of transactions**

    5,000 lines from her bank's export. One line, 4,812, has a date written 31.03.2026.

2.  **The app says "Something went wrong"**

    The parser stopped at that line and threw an exception nobody caught. Nothing was imported, and nothing says which line to fix.

3.  **The fix**

    Read every line. Keep the good ones, and list each bad one with its line number, the field and what was wrong, so Meera fixes one line, once.

An error the customer can act on names the line, the field and the value.

## What are we building?

`POST /statements/parse` takes a statement CSV and returns the transactions it could read, plus a list of every line it could not read and why.

## An everyday analogy

A teacher marking 50 answer sheets does not stop at the first mistake and hand everything back with "wrong". She marks every sheet and writes the question number next to each mistake.

## How it works in 4 steps

1.  **Check the header**: the first line must name the five columns.
2.  **Read each line**: split the fields, parse the date strictly, turn amounts into paise.
3.  **Catch per line**: a bad line becomes an error with its line number; the loop carries on.
4.  **Report**: COMPLETE, PARTIAL or REJECTED, with the transactions and the errors.

Check yourself: why is quietly reading 31/02/2026 as 28/02/2026 worse than an error?

The statement now contains a transaction on a day it did not happen, and nobody knows. An error is annoying once; a silent change is wrong forever.

## What this station is not

- **No storage.** The result is returned, not saved.
- **Not a full CSV library.** Line breaks inside quoted fields are not supported (a demo rule).
- **One bank format.** Challenge 2 accepts other banks' column names.

## Key terms

| Term                  | Simple meaning                                                                   | Everyday example                                         | In this project         |
|-----------------------|----------------------------------------------------------------------------------|----------------------------------------------------------|-------------------------|
| **CSV**               | Text where each line is a row and commas separate the fields.                    | A bank statement exported for a spreadsheet.             | `text/csv` request body |
| **Quoted field**      | A field in double quotes, so it can contain commas; `""` inside it is one quote. | `"UPI/GROCER, BLR"`                                      | `CsvLine`               |
| **Date format**       | The pattern a date is written in.                                                | 31/03/2026 (dd/MM/yyyy) or 2026-03-31.                   | `DATE_FORMATS`          |
| **Strict parsing**    | Refuse impossible dates instead of adjusting them.                               | 31 February is an error, not 28 February.                | `ResolverStyle.STRICT`  |
| **Checked exception** | An exception the compiler makes the caller handle or declare.                    | A form that cannot be filed until every box is answered. | `LineException`         |
| **Per-line error**    | A problem reported with the line, field and value it came from.                  | "Line 4,812: date 31.03.2026 is not a real date".        | `errors`                |

# 2 · Build: Spec

## Business problem

**Tijori** (a fictional fintech app) imports bank statements for budgeting. Its parser stops at the first bad line and the error reaches the customer as "Something went wrong". Support cannot tell which line was wrong either, so customers retry the same file, again and again.

## Acceptance criteria

1.  **Given** 5,000 lines with a bad date on line 4,812, **then** 4,999 transactions, status PARTIAL, and one error naming line 4,812, the field `date` and the value.
2.  **Given** 31/02/2026, 29/02/2025 or 01/13/2026, **then** an error, never an adjusted date.
3.  **Given** "1,23,456.50", **then** 12,345,650 paise; "12.345", "-5" or "ten" is an error.
4.  **Given** quoted fields with commas or `""`, **then** they are read whole.
5.  **Given** no header, or more than 10,000 lines, **then** `422`; an empty body `400`; JSON `415`.
6.  **Given** 150 bad lines, **then** errorCount 150 and the first 100 listed.

## Requirements

- Line numbers are as a spreadsheet shows them: the header is line 1.
- Dates: dd/MM/yyyy, dd-MM-yyyy or yyyy-MM-dd, strictly.
- Exactly one of debit and credit has an amount. Amounts are whole paise.
- Error values are cut to 40 characters; at most 100 errors are listed (demo rules).

## Learning objectives

- Parse and trim text fields, including quoted CSV fields.
- Parse dates with several formats, strictly, and know why STRICT needs `uuuu`.
- Explain checked versus unchecked exceptions, and use a checked one on purpose.
- Collect per-line errors instead of failing on the first.

# 2 · Build: API contract

## Endpoint

| Method | Path                | Purpose                                                                    |
|--------|---------------------|----------------------------------------------------------------------------|
| `POST` | `/statements/parse` | Parse a `text/csv` statement. `200` with what was read and every bad line. |

## Request body

A CSV file whose first line is `date,description,debit,credit,balance`, at most 10,000 more lines.

## Response

| Field                  | Meaning                                                                                 |
|------------------------|-----------------------------------------------------------------------------------------|
| `status`               | `COMPLETE` (no errors), `PARTIAL` (some lines read), `REJECTED` (none read).            |
| `linesRead`            | Lines after the header.                                                                 |
| `transactions`         | Each with its file `line`, ISO `date`, description and amounts in paise.                |
| `errorCount`, `errors` | How many lines failed; the first 100, each with `line`, `field`, `value` and `message`. |

## Status codes

| Status | When                                            |
|--------|-------------------------------------------------|
| 200    | The file was read; the body says how much of it |
| 400    | Empty body                                      |
| 415    | Not `text/csv`                                  |
| 422    | No valid header, or more than 10,000 lines      |

## Captured examples

Captured with curl from the running app on 14 Oct 2026. The request bodies are the files in `docs/samples/`; JSON responses are indented for reading; `Date` and connection headers are left out.

### Case 1: a clean statement

**Why:** three date formats, a quoted description with a comma, Indian grouping in amounts: all read. COMPLETE.

Request

``` code
POST /statements/parse HTTP/1.1
Content-Type: text/csv

date,description,debit,credit,balance
01/04/2026,"UPI/GROCER, BLR","1,234.50",,98765.50
2026-04-02,Salary,,"1,20,000",218765.50
03-04-2026,ATM withdrawal,500,,218265.50
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 438

{
  "status": "COMPLETE",
  "linesRead": 3,
  "transactions": [
    {
      "line": 2,
      "date": "2026-04-01",
      "description": "UPI/GROCER, BLR",
      "debitPaise": 123450,
      "creditPaise": 0,
      "balancePaise": 9876550
    },
    {
      "line": 3,
      "date": "2026-04-02",
      "description": "Salary",
      "debitPaise": 0,
      "creditPaise": 12000000,
      "balancePaise": 21876550
    },
    {
      "line": 4,
      "date": "2026-04-03",
      "description": "ATM withdrawal",
      "debitPaise": 50000,
      "creditPaise": 0,
      "balancePaise": 21826550
    }
  ],
  "errorCount": 0,
  "errors": []
}
```

### Case 2: three bad lines among five

**Why:** an impossible date, an amount with three decimals, and a line with both debit and credit. Each is listed with its line number; the two good lines are kept. PARTIAL.

Request

``` code
POST /statements/parse HTTP/1.1
Content-Type: text/csv

date,description,debit,credit,balance
01/04/2026,Rent,25000,,75000
31/02/2026,Electricity,1200,,73800
02/04/2026,Fuel,"2,000.505",,71799.50
03/04/2026,Refund,500,500,72299.50
04/04/2026,Groceries,800,,71499.50
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 623

{
  "status": "PARTIAL",
  "linesRead": 5,
  "transactions": [
    {
      "line": 2,
      "date": "2026-04-01",
      "description": "Rent",
      "debitPaise": 2500000,
      "creditPaise": 0,
      "balancePaise": 7500000
    },
    {
      "line": 6,
      "date": "2026-04-04",
      "description": "Groceries",
      "debitPaise": 80000,
      "creditPaise": 0,
      "balancePaise": 7149950
    }
  ],
  "errorCount": 3,
  "errors": [
    {
      "line": 3,
      "field": "date",
      "value": "31/02/2026",
      "message": "is not a real date in dd/MM/yyyy, dd-MM-yyyy or yyyy-MM-dd"
    },
    {
      "line": 4,
      "field": "debit",
      "value": "2,000.505",
      "message": "is not an amount like 1,234.50"
    },
    {
      "line": 5,
      "field": "debit",
      "value": "500 / 500",
      "message": "exactly one of debit and credit must have an amount"
    }
  ]
}
```

### Case 3: no header

**Why:** without the header the columns cannot be trusted: `422` for the whole file.

Request

``` code
POST /statements/parse HTTP/1.1
Content-Type: text/csv

01/04/2026,Rent,25000,,75000
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "The first line must be the header date,description,debit,credit,balance.",
  "instance": "/statements/parse",
  "status": 422,
  "title": "Statement file cannot be read"
}
```

### Case 4: JSON instead of CSV

**Why:** the endpoint only consumes `text/csv`: `415`.

Request

``` code
POST /statements/parse HTTP/1.1
Content-Type: application/json

{
  "rows": []
}
```

Response

``` code
HTTP/1.1 415 
Accept: text/csv
Content-Type: application/problem+json

{
  "detail": "Content-Type 'application/json' is not supported.",
  "instance": "/statements/parse",
  "status": 415,
  "title": "Unsupported Media Type"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                                                   | What happens                       | Proved by                                                            |
|----------------------------------------------------------------------------------------|------------------------------------|----------------------------------------------------------------------|
| 5,000 lines, bad date on 4,812                                                         | 4,999 read; error on line 4,812    | `theFixedParserReadsEveryOtherLineAndNamesTheBadOne`                 |
| Quotes, `""`, three date formats, grouping                                             | All read                           | `aCleanStatementIsComplete`                                          |
| Impossible date, both amounts, 3 decimals, unclosed quote, 3 fields, empty description | Six errors, each with its line     | `everyBadLineIsListedWithItsLineNumber`                              |
| 150 bad lines                                                                          | REJECTED; 150 counted, 100 listed  | `aFileWithNoGoodLinesIsRejectedAndOnlyTheFirstHundredErrorsAreShown` |
| No header; 10,001 lines; 10,000 lines                                                  | `422`; `422`; read                 | `aMissingHeaderOrATooLongFileIs422`                                  |
| Empty body; JSON                                                                       | `400`; `415`                       | `anEmptyBodyIs400AndAnotherContentTypeIs415`                         |
| 29/02 in 2024 and 2025; 31/04; 1/4/2026; 04/01/26                                      | Leap day read; the rest refused    | `datesAreStrictInEveryFormat`                                        |
| 1,23,456.50; 12.345; -5; 1e3; ₹10                                                      | 12,345,650 paise; the rest refused | `amountsAreWholePaiseWithIndianGrouping`                             |

## The trap

Plausible but wrong

Failing the whole file on one bad line, with no line number in the error.

The first test shows the old loop throwing at line 4,812 with a message that does not mention the line. It is an unchecked exception, so nothing forced anyone to handle it. The second shows the default date formatter quietly turning 31 February into 28 February. The third shows the fixed parser reading 4,999 lines and naming line 4,812. While building, stopping at the first error turned 3 tests red, dropping STRICT turned 2 red, and counting lines from 1 instead of 2 turned 3 red.

``` code
package com.tijori.statementimport;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The first test written for this station: it reproduces the bugs before the fix. */
class OneBadLineTrapTest extends ApiTest {

    /** A 5,000-line statement whose line 4,812 has a date with the wrong separator. */
    static final String UPLOAD = statement(5_000, 4_812, "31.03.2026,UPI to grocer,10.00,,90000.00");

    /** The "before" parser: the first exception ends everything. Kept only in tests. */
    static int oldParse(String csv) {
        DateTimeFormatter format = DateTimeFormatter.ofPattern("dd/MM/yyyy");
        int read = 0;
        for (String line : csv.lines().skip(1).toList()) {
            LocalDate.parse(line.split(",")[0], format);
            read++;
        }
        return read;
    }

    @Test
    void theOldParserGivesUpAtTheFirstBadLineAndDoesNotSayWhichOne() {
        assertThatThrownBy(() -> oldParse(UPLOAD))
                .isInstanceOf(DateTimeParseException.class)   // unchecked: nothing forced anyone to handle it, so it became a 500
                .hasMessageNotContaining("4812")
                .hasMessageNotContaining("4,812");
    }

    @Test
    void theOldDateFormatQuietlyTurnsThirtyFirstFebruaryIntoTheTwentyEighth() {
        // The default SMART resolver "fixes" an impossible date instead of reporting it.
        assertThat(LocalDate.parse("31/02/2026", DateTimeFormatter.ofPattern("dd/MM/yyyy"))).isEqualTo(LocalDate.of(2026, 2, 28));
    }

    @Test
    void theFixedParserReadsEveryOtherLineAndNamesTheBadOne() throws Exception {
        parse(UPLOAD)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("PARTIAL"))
                .andExpect(jsonPath("$.linesRead").value(5000))
                .andExpect(jsonPath("$.transactions.length()").value(4999))
                .andExpect(jsonPath("$.errorCount").value(1))
                .andExpect(jsonPath("$.errors[0].line").value(4812))
                .andExpect(jsonPath("$.errors[0].field").value("date"))
                .andExpect(jsonPath("$.errors[0].value").value("31.03.2026"));
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

Use `--data-binary`, not `-d`: `-d @file` removes the line breaks, and the whole file becomes one line.

``` code
curl -X POST http://localhost:8080/statements/parse -H "Content-Type: text/csv" --data-binary @docs/samples/three-bad-lines.csv
```

## Troubleshooting

| You see                                     | Cause                                                | Fix                                   |
|---------------------------------------------|------------------------------------------------------|---------------------------------------|
| Every line is one error, "has 21 fields"    | `curl -d @file` joined all lines.                    | Use `--data-binary @file`.            |
| `422` about the header                      | The first line is not exactly the five column names. | Export with headers, or add the line. |
| Every date fails after you change a pattern | STRICT with `yyyy` (year of era) needs an era.       | Use `uuuu`.                           |

## Project layout

``` tree
stations/021-parsing-a-bank-statement-csv/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tijori/statementimport/
│   ├── StatementController.java   ├── StatementParser.java
│   ├── CsvLine.java               ├── LineException.java   └── StatementImportApplication.java
├── src/test/java/com/tijori/statementimport/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     samples/, capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/tijori/statementimport/StatementController.java`

Does  
Accepts `text/csv`, parses it, and turns a file-level problem into a `422`.

Why  
The controller has no parsing logic: the parser is plain Java, testable without Spring.

Without it  
A generic 500 "Something went wrong".

#### `src/main/java/com/tijori/statementimport/StatementParser.java`

Does  
The header check, the per-line loop, strict dates and amounts.

Why  
A checked `LineException` per line: the loop must catch it, so one bad line can never end the file.

Without it  
The trap: the first exception ends everything.

- `DATE_FORMATS` are tried in order; each is STRICT (ISO_LOCAL_DATE is strict already).
- File-level problems are an unchecked `FileProblem`: there is nothing to continue with.
- `lines()`, not `strip()`: a leading blank line must not shift line numbers.

#### `src/main/java/com/tijori/statementimport/CsvLine.java`

Does  
Splits one line into fields, honouring quotes.

Why  
Twenty lines of plain Java instead of a dependency, for one simple format.

Without it  
`line.split(",")`, which breaks on `"UPI/GROCER, BLR"`.

#### `src/main/java/com/tijori/statementimport/LineException.java`

The checked exception: field, value and message for one line.

#### `src/main/resources/application.yaml`

Problem bodies for every error.

#### `src/main/java/com/tijori/statementimport/StatementImportApplication.java`

Standard Spring Boot entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                 | Test class                  | Result |
|---------------|-------------------------------------------------------------|-----------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found (a missing header) | `StatementContractTest` (5) | pass   |
| Every station | Reproduce the failure before the fix                        | `OneBadLineTrapTest` (3)    | pass   |
| This station  | CSV splitting, strict dates, amounts                        | `StatementParserTest` (3)   | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.statementimport.OneBadLineTrapTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.statementimport.StatementContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.tijori.statementimport.StatementParserTest
[INFO] Tests run: 11, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/tijori/statementimport/OneBadLineTrapTest.java`

Written first: the old loop's nameless exception, the silent 28 February, and the fixed parser on 5,000 lines.

#### `src/test/java/com/tijori/statementimport/StatementContractTest.java`

A clean file, a file with six kinds of bad line, a rejected file, and files that cannot be read.

#### `src/test/java/com/tijori/statementimport/StatementParserTest.java`

The parsing pieces with no Spring at all.

#### `src/test/java/com/tijori/statementimport/ApiTest.java`

Shared setup and a generator for long statements with one bad line.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/tijori/statementimport/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=RunningBalanceChallengeTest`
3.  Change the code until it passes, then run `./mvnw test` to check the other 11 tests.

Checked (`docs/challenge-run.txt`): with the reference solution copied in, all 15 tests pass (11 station tests and 4 challenge tests).

Challenge 1 · Go deeper · about 30 minutes

## Check the running balance

Each line's balance must equal the line before's balance, minus its debit, plus its credit. A mismatch is an error on that line saying what it should be. After an unreadable line, skip the check for the next one.

**Done when:** both tests in `RunningBalanceChallengeTest` pass, and the station's tests still pass.

Hints

- Keep the previous line's stated balance in a `Long`; set it to `null` after an error.
- Compare with the stated balance, not your own running total, so one wrong line is one error, not a cascade.

#### `challenge/RunningBalanceChallengeTest.java`

``` code
package com.tijori.statementimport;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 1: each line's balance must be the line before's balance, minus its debit, plus its credit.
 * A mismatch is an error on that line saying what the balance should be. After a line that could not be read,
 * the next line is not checked (there is nothing reliable to compare with). Each line follows the balance the
 * file states on the line before, so one wrong balance is one error, not a cascade.
 */
class RunningBalanceChallengeTest extends ApiTest {

    @Test
    void aBalanceThatDoesNotFollowIsAnError() throws Exception {
        parse(HEADER + """
                01/04/2026,Opening,,1000,1000
                02/04/2026,Rent,250,,750
                03/04/2026,Groceries,100.50,,649.50
                04/04/2026,Refund,,49.50,700.00
                05/04/2026,Fuel,200,,500.00
                """)
                .andExpect(jsonPath("$.status").value("PARTIAL"))
                .andExpect(jsonPath("$.errorCount").value(1))
                .andExpect(jsonPath("$.errors[0].line").value(5))
                .andExpect(jsonPath("$.errors[0].field").value("balance"))
                .andExpect(jsonPath("$.errors[0].message").value("should be 699.00 (649.50 - 0.00 + 49.50)"));
    }

    @Test
    void theLineAfterAnUnreadableLineIsNotChecked() throws Exception {
        parse(HEADER + """
                01/04/2026,Opening,,1000,1000
                bad date,Rent,250,,750
                03/04/2026,Groceries,100,,650
                04/04/2026,Fuel,50,,600
                """)
                .andExpect(jsonPath("$.errorCount").value(1))
                .andExpect(jsonPath("$.errors[0].field").value("date"));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Beginner-friendly · about 25 minutes

## Columns by name

Find the five columns by name in any order, accepting other banks' names: Txn Date, Narration, Withdrawal Amt, Deposit Amt, Closing Balance. Extra columns are ignored; a missing one is `422` naming it.

**Done when:** both tests in `ColumnsByNameChallengeTest` pass.

Hints

- Turn the header into a list of lower-case names and look up each column's index.
- Pass the indexes into `parseLine` instead of the fixed 0 to 4.

#### `challenge/ColumnsByNameChallengeTest.java`

``` code
package com.tijori.statementimport;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: find columns by name, in any order, with other banks' names for them:
 * "Txn Date", "Narration", "Withdrawal Amt", "Deposit Amt", "Closing Balance". Extra columns are ignored.
 */
class ColumnsByNameChallengeTest extends ApiTest {

    @Test
    void anotherBanksHeaderInAnotherOrderIsRead() throws Exception {
        parse("""
                Narration,Txn Date,Ref No,Deposit Amt,Withdrawal Amt,Closing Balance
                Salary,01/04/2026,REF1,"1,20,000",,120000
                Rent,02/04/2026,REF2,,25000,95000
                """)
                .andExpect(jsonPath("$.status").value("COMPLETE"))
                .andExpect(jsonPath("$.transactions[0].description").value("Salary"))
                .andExpect(jsonPath("$.transactions[0].creditPaise").value(12000000))
                .andExpect(jsonPath("$.transactions[1].debitPaise").value(2500000));
    }

    @Test
    void aMissingColumnIs422NamingIt() throws Exception {
        parse("""
                Txn Date,Narration,Withdrawal Amt,Deposit Amt
                01/04/2026,Salary,,1000
                """)
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.detail").value("The header has no balance column (also accepted: closing balance)."));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Import the good lines, or nothing?

This station reports PARTIAL and lets the app decide. For a budgeting app, importing 4,999 of 5,000 lines may be fine; for a loan application that checks income, a missing salary line changes the answer. Who should decide, and how would the API let them: a flag, two endpoints, or a confirm step?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the nameless exception at line 4,812, and the silent 28 February.
2.  Write the line splitter and strict date and amount parsers; test them without Spring.
3.  Make a bad line a checked exception, caught in the loop with the line number.
4.  Report status, transactions and errors; refuse files without a header or that are too long.

## Design alternatives and trade-offs

| Approach                                       | What it costs                                         | Verdict           |
|------------------------------------------------|-------------------------------------------------------|-------------------|
| Read every line, report each error             | A result with two lists instead of one.               | Chosen            |
| Fail on the first error                        | One fix per upload; no line number unless you add it. | The trap          |
| `line.split(",")`                              | Breaks on quoted commas.                              | Wrong             |
| A CSV library (for example Apache Commons CSV) | A dependency; handles line breaks in quotes and more. | For messier files |
| Default (SMART) date parsing                   | Impossible dates are adjusted silently.               | Wrong for money   |

## Database design

None in this station. When imports are stored: an `imports` row per upload (status, counts) and its `import_errors` (line, field, value, message), so support can see exactly what a customer saw.

# 3 · Go deeper: Production

Size  
The whole body is read before the line limit applies. Cap the upload size at the proxy or server, or read the stream line by line, before accepting large files.

Privacy  
Statements are personal financial data. Do not log the body; error values are cut to 40 characters and show only the field that failed.

Encoding  
Exports may start with a byte-order mark; the header check removes it. Files that are not UTF-8 need an explicit charset.

Support  
Line numbers match what a spreadsheet shows, so support and customers point at the same row.

# 3 · Go deeper: Interview

## Interview takeaways

Checked or unchecked: what is the difference?

A checked exception must be caught or declared, so the compiler makes callers think about it. An unchecked one (RuntimeException) can travel up unnoticed. Use checked for failures the caller is expected to handle, like a bad line.

Why is 31/02/2026 parsed as 28 February by default?

DateTimeFormatter.ofPattern uses ResolverStyle.SMART, which clamps an invalid day to the last day of the month. STRICT refuses it.

Why uuuu instead of yyyy with STRICT?

yyyy is year of era and needs an era field to resolve strictly; without one every date fails. uuuu is the proleptic year and needs nothing else.

How should a parser report errors?

With the line number, the field, the value and what was expected, for every bad line, so the user can fix them all in one go.

Why not split CSV on commas?

Fields may be quoted because they contain commas. A small state machine that tracks whether you are inside quotes handles it.

## Self-check rubric

| Area        | Meets the bar                           | Above the bar                                             |
|-------------|-----------------------------------------|-----------------------------------------------------------|
| Correctness | All 11 tests pass.                      | You can predict the errors for case 2 before running it.  |
| Dates       | Strict parsing in several formats.      | You can explain SMART, STRICT and uuuu.                   |
| Exceptions  | Per-line errors with line numbers.      | When a checked exception is the right tool, and when not. |
| Explanation | Why one bad line must not end the file. | Partial import: who decides, and how.                     |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any file import:

- Does one bad line end the whole import?
- Does every error name the line, the field and the value?
- Are dates parsed strictly, and are amounts kept exact?
- Is there a limit on size, and is the file kept out of the logs?
