# Station 021 plan: Parsing a bank statement CSV

**Problem.** Tijori's statement upload parses with `LocalDate.parse` in a loop; one bad date on line 4,812 throws an
unchecked DateTimeParseException, the whole upload fails, and the customer sees "Something went wrong" with no line.
The default SMART resolver also turns 31/02 into 28 Feb without a word.

**Endpoint.** `POST /statements/parse` (text/csv: header date,description,debit,credit,balance) 200 with status
COMPLETE / PARTIAL / REJECTED, the transactions read, and every bad line (line number, field, value, message; first
100 shown, errorCount total); 400 empty body; 415 not CSV; 422 no header or more than 10,000 lines. Nothing stored.

**Data.** `CsvLine.split` (quotes, "" escapes, trimming). Strict dates in dd/MM/uuuu, dd-MM-uuuu, yyyy-MM-dd. Amounts
with Indian grouping to paise; exactly one of debit/credit. A checked `LineException` per line, caught by the loop.

**Trap.** `OneBadLineTrapTest`: old parser throws at line 4,812 with no line number; SMART gives 28 Feb; the fixed parser
reads 4,999 lines and names line 4,812. Mutations: stop at first error -> 3 red; no STRICT -> 2 red; line numbers
off by one -> 3 red.

**Tests.** Trap, `StatementContractTest`, `StatementParserTest` (CSV splitting, strict dates, amounts).

**Practice.** 1: running balance check. 2: columns by name, any order, with other banks' header names.
Design: accepting a partial statement or not.
