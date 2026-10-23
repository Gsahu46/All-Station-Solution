# Station 093 plan: Order export to CSV

**Problem.** Kartwala (fictional): exporting a year of orders ran out of memory (every row in a list, the file in one
String), and a product named =HYPERLINK(...) became a working link when a seller opened the file in Excel.

**Endpoint.** `GET /seller/orders/export?from&to` (ISO dates, IST days, at most 366 days including both ends): 200,
text/csv; charset=UTF-8, attachment orders-FROM-to-TO.csv, a UTF-8 byte order mark (Excel), header row, oldest first.
Bad or too long range 400 (logged nothing). HTTP Basic: sellers neha.store (1), arun.mart (2) export their own
orders only (the seller from the sign-in); sam.help (support) 403; none 401.

**Streaming.** StreamingResponseBody; a read-only transaction; spring.jdbc.template.fetch-size 1000 so the PostgreSQL
driver uses a cursor; each row written through a BufferedWriter and forgotten. The export is recorded in export_log
before it starts (range CHECK in the database).

**Cells.** Csv.text: text starting with = + - @ tab or CR gets a leading ' (OWASP CSV injection advice), then RFC 4180
quoting. Numbers and states are written by our code and not escaped.

**Trap.** `FormulaAndMemoryTrapTest`: the old list-and-join way passes =HYPERLINK on and splits "kurta, blue"; the API
quotes and neutralises.

**Found while building.** (1) A first streaming test checked pg_stat_activity for the open query: it could not tell
streaming from load-all (the transaction stays open in both). Replaced by timing: a million rows; the first lines
arrive about as fast as an empty export, while reading all rows takes seconds. (2) With a fresh table and no
statistics the planner guessed 15 rows and sorted the whole year before the first row, so streaming gained nothing;
after ANALYZE (as autovacuum would) it reads the index in order. (3) No fetch size, or no transaction: the driver
reads every row before the first one is handed over (first lines after about 2 s instead of about 50 ms).

**Mutations.** no fetch size -> 1; no transaction -> 1; no formula guard -> 3; no quoting -> 2; no BOM -> 3; UTC days
-> 4; any seller -> 3; no range check -> 1; no export log -> 2. An index with id added changed no test after ANALYZE.

**Review.** Rows loaded into a list first; formulas only quoted: 4 of 12 fail.

**Practice.** 1: ?status= filter. 2: GET /seller/exports with rows sent (V3). 3 (paper): exports as background jobs.
