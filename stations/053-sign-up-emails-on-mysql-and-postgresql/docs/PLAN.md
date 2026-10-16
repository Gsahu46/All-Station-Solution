# Station 053 plan: Sign-up emails on MySQL and PostgreSQL

**Problem.** Taskloom runs on MySQL for some customers and PostgreSQL for others with "email VARCHAR UNIQUE". On MySQL
(default collation utf8mb4_0900_ai_ci) Asha@x.com and asha@x.com are one user; on PostgreSQL, two. The check before
the insert used email = ?, so PostgreSQL also missed the duplicate there. MySQL's collation also ignores accents.

**Endpoint.** `POST /signups` {email (ASCII only, demo rule; trimmed), name} 201 + Location, email kept as typed;
409 the same email in any case; 400 malformed. Added `GET /signups/{id}` read-back for the not-found case.

**Code.** JdbcClient; lookups use lower(email) = ? (Locale.ROOT lower-case in Java); DuplicateKeyException -> 409 for
the race. Flyway locations db/migration/{vendor}: one V1 per database. PostgreSQL: unique index on lower(email).
MySQL: email column COLLATE utf8mb4_bin (exact, like PostgreSQL) plus a functional unique index ((lower(email))), same
name. Both: CHECK signups_email_shape. App runs on PostgreSQL by default, MySQL with the mysql profile.

**Tests.** CaseSensitivityTrapTest (plain JDBC on both containers: the old table keeps two Ashas on PostgreSQL, one on
MySQL; MySQL also merges jose/josé; the old email = ? lookup misses). SignupContract and SignupDatabase written once,
run on both through Postgres*/MySql* subclasses (@Import of a shared container). Mutations: plain unique on PostgreSQL
-> 3 red (the Java lookup still gives 409 over HTTP); MySQL default collation -> 1 (the accent test); no
DuplicateKeyException catch -> 2 (the race, both databases); lookup with email = ? -> 0 (the index answers 409).

**Practice.** 1: find by email ignoring case. 2: change email (own case change allowed, someone else's refused).
Design: when supporting two databases is worth it.
