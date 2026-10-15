# Station 036 plan: Medicine search with plain JDBC

**Problem.** Mediqo's pharmacy search built SQL by concatenating the user's text: a UNION payload returned every
patient's name, phone and doctor from prescriptions; an apostrophe broke the query; and nothing was closed, so each
search kept a pooled connection until the pool ran dry.

**Endpoint.** `GET /medicines?name=` (2 to 50 characters after trimming) 200 {query, results[{id, name, strength,
form, pricePaise, prescriptionRequired}]} at most 20, ordered by name, strength, form; no match is an empty list;
400 missing, blank, too short or too long.

**Code.** `MedicineSearch` uses the DataSource directly: fixed SQL text, `PreparedStatement` parameters,
`lower(name) LIKE ? ESCAPE '\'` with `%`, `_` and `\` escaped, try-with-resources for connection, statement and
result set.

**Database.** Flyway V1: `medicines` (identity PK, `medicines_price_positive`, `medicines_form_known`, unique
index `medicines_unique_product` on lower(name), strength, form) and `prescriptions`
(`prescriptions_medicine_fk`). V2: 15 demo medicines, 3 fictional prescriptions.

**Trap.** `ConcatenatedSqlTrapTest` on real PostgreSQL: the old search dumps prescriptions with a UNION payload;
`x' OR 1=1 --` (12 characters) returns every medicine; an apostrophe is an "Unterminated string literal"; on a
3-connection pool the 4th old search times out; the real search returns all connections after 50 searches.
Mutations: no LIKE escaping -> 1 red; connection not closed -> 8; concatenated SQL -> 5.

**Database tests.** `MedicineDatabaseTest`: named constraints refuse bad rows via plain JDBC; FK; a failed statement
in a manual transaction leaves nothing after rollback; with auto-commit the first row stays.

**Practice.** 1: optional form filter (fixed fragments, values as parameters). 2: size and total with
count(*) OVER (). Design: search that scales (pg_trgm, full-text).
