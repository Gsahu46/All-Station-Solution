# Station 053 · Sign-up emails on MySQL and PostgreSQL

Foundations · 0–1 years · Core · SaaS · Types: Database

Spring Boot 4.1.1 · Java 25 · JdbcClient · PostgreSQL 17 and MySQL 8.4 · Flyway per vendor · Testcontainers (both databases, shared containers). Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL and MySQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Sign-ups are demo records; no email is sent to confirm an address.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 22 tests.

# 1 · Understand

## The problem in real life

1.  **Two databases, one schema**

    Taskloom runs on MySQL for some customers and PostgreSQL for others, with the same table: `email VARCHAR(254) UNIQUE`.

2.  **One user or two?**

    On MySQL, Asha@x.com and asha@x.com were one user. On PostgreSQL, they were two accounts, and Asha's projects were split between them. Support also found MySQL refusing josé@x.com because jose@x.com existed.

3.  **The fix**

    Say exactly what "the same email" means (the same after lower-casing, nothing else), write it into each database's schema in that database's own words, and run the same tests on both.

"UNIQUE" means "unique under this database's comparison rules", and the rules differ.

## What are we building?

`POST /signups` takes an email and a name. The same email in any case is refused with `409`, on PostgreSQL and on MySQL alike. The address is kept as the person typed it.

## An everyday analogy

Two school offices keep the same register. One files every name in capitals; the other files names exactly as written, so "ASHA" and "Asha" get two pages. Same register, different filing rule. The fix is to agree on the rule and write it on both registers' covers.

## How it works in 4 steps

1.  **Trim** the address and check its shape (ASCII only, a demo rule).
2.  **Look up** `lower(email)`: is this person already here?
3.  **Insert**; the unique index on `lower(email)` refuses a duplicate, even one sent at the same moment.
4.  **Answer** `201`, or `409` for either refusal.

Check yourself: MySQL already ignores case. Why change its schema at all?

Its default also ignores accents, and its rules depend on a collation setting someone can change. Making the column exact (`utf8mb4_bin`) and the index explicit (`lower(email)`) gives the same rule PostgreSQL has, written down, not inherited.

## What this station is not

- **No email verification.** Addresses are not confirmed.
- **No international addresses.** Non-ASCII emails are refused (a demo rule).
- **No login.** A sign-up is a record.

## Key terms

| Term                   | Simple meaning                                                | Everyday example                                              | In this project                     |
|------------------------|---------------------------------------------------------------|---------------------------------------------------------------|-------------------------------------|
| **Collation**          | A database's rules for comparing and sorting text.            | A dictionary that files "Asha" and "asha" together, or apart. | `utf8mb4_0900_ai_ci`, `utf8mb4_bin` |
| **Case-insensitive**   | Upper and lower case count as the same letter.                | "ASHA" and "asha" are one name.                               | MySQL's default                     |
| **Accent-insensitive** | Letters with and without accents count as the same.           | "jose" and "josé" are one name.                               | The `ai` in MySQL's default         |
| **Expression index**   | An index on a computed value, not the raw column.             | An index card filed under the name in lower case.             | `lower(email)`                      |
| **Testcontainers**     | Real databases in Docker, started by the tests.               | A practice kitchen with the real stove.                       | `Databases`                         |
| **Portability**        | The same code giving the same answers on different databases. | A recipe that works on gas and induction.                     | Same tests on both                  |

# 2 · Build: Spec

## Business problem

**Taskloom** (a fictional SaaS) supports both MySQL and PostgreSQL. Sign-up uniqueness behaved differently on each, creating duplicate accounts on one and refusing real addresses on the other.

## Acceptance criteria

1.  **Given** Asha@x.com signed up, **then** asha@x.com, ASHA@X.COM and " asha@x.com " are `409`, on both databases.
2.  **Given** 10 spellings of the same address at the same moment, **then** one sign-up, nine `409`, on both.
3.  **Given** jose@x.com and josé@x.com written directly to the table, **then** two rows, on both.
4.  **Given** an address without @, with non-ASCII letters, over 254 characters, or a blank name, **then** `400`.
5.  **Given** an unknown sign-up id, **then** `404`.

## Requirements

- "The same email" means equal after lower-casing, and nothing more, on every database.
- The rule is a named unique index in each schema: `signups_email_unique`.
- Each database gets its own migration, in its own SQL.
- Every contract and database test runs on both databases.

## Learning objectives

- Explain collations, and how MySQL and PostgreSQL compare text by default.
- Enforce case-insensitive uniqueness with an expression index on both.
- Run the same tests on two real databases with Testcontainers.
- Know where portability ends.

# 2 · Build: API contract

## Endpoints

| Method | Path            | Purpose                                                             |
|--------|-----------------|---------------------------------------------------------------------|
| `POST` | `/signups`      | Sign up: `email` (trimmed, ASCII, up to 254 characters) and `name`. |
| `GET`  | `/signups/{id}` | Read a sign-up back (added so "not found" has something to miss).   |

## Status codes

| Status | When                                           |
|--------|------------------------------------------------|
| 201    | Signed up; `Location` points at it             |
| 200    | The sign-up                                    |
| 400    | Email or name missing or malformed             |
| 404    | No such sign-up                                |
| 409    | This email, in any case, has already signed up |

## Captured examples

Captured with curl on 16 Oct 2026, in this order: the same jar running twice, on PostgreSQL (port 8080) and on MySQL (port 8081). JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: PostgreSQL, Asha@x.com

**Why:** `201`, kept as typed.

Request

``` code
POST /signups HTTP/1.1
Content-Type: application/json

{
  "email": "Asha@x.com",
  "name": "Asha Verma"
}
```

Response

``` code
HTTP/1.1 201 
Location: /signups/1
Content-Type: application/json

{
  "id": 1,
  "email": "Asha@x.com",
  "name": "Asha Verma"
}
```

### Case 2: PostgreSQL, asha@x.com

**Why:** the same person: `409`. The old schema let this in.

Request

``` code
POST /signups HTTP/1.1
Content-Type: application/json

{
  "email": "asha@x.com",
  "name": "Asha Verma"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "asha@x.com has already signed up (emails are compared ignoring case).",
  "instance": "/signups",
  "status": 409,
  "title": "Already signed up"
}
```

### Case 3: MySQL, Asha@x.com

**Why:** `201`.

Request

``` code
POST /signups HTTP/1.1
Content-Type: application/json

{
  "email": "Asha@x.com",
  "name": "Asha Verma"
}
```

Response

``` code
HTTP/1.1 201 
Location: /signups/1
Content-Type: application/json

{
  "id": 1,
  "email": "Asha@x.com",
  "name": "Asha Verma"
}
```

### Case 4: MySQL, asha@x.com

**Why:** `409`: the same answer as PostgreSQL, from the same rule.

Request

``` code
POST /signups HTTP/1.1
Content-Type: application/json

{
  "email": "asha@x.com",
  "name": "Asha Verma"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "asha@x.com has already signed up (emails are compared ignoring case).",
  "instance": "/signups",
  "status": 409,
  "title": "Already signed up"
}
```

### Case 5: asha.x.com

**Why:** `400`.

Request

``` code
POST /signups HTTP/1.1
Content-Type: application/json

{
  "email": "asha.x.com",
  "name": "Asha Verma"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Invalid request content.",
  "instance": "/signups",
  "status": 400,
  "title": "Bad Request"
}
```

### Case 6: sign-up 99

**Why:** `404`.

Request

``` code
GET /signups/99 HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No sign-up 99.",
  "instance": "/signups/99",
  "status": 404,
  "title": "Sign-up not found"
}
```

## What "equal" means to each database

Asked directly with psql and the mysql client (connected in utf8mb4, as the app is) after the requests above (`docs/captures/equality.txt`): the default text comparison, with no table and no index.

``` code
-- PostgreSQL 17
 case_ignored | accents_ignored 
--------------+-----------------
 f            | f
(1 row)

-- MySQL 8.4, default collation utf8mb4_0900_ai_ci
+--------------+-----------------+
| case_ignored | accents_ignored |
+--------------+-----------------+
|            1 |               1 |
+--------------+-----------------+
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                 | What happens                 | Proved by                                       |
|------------------------------------------------------|------------------------------|-------------------------------------------------|
| Mixed-case address                                   | Kept as typed                | `aSignupKeepsTheEmailAsTyped`                   |
| Another case, or with spaces                         | `409`, one row               | `theSameEmailInAnyCaseIs409`                    |
| Similar but different addresses                      | All accepted                 | `differentEmailsAreDifferent`                   |
| No @, non-ASCII, too long, blank name, missing email | `400`, no row                | `badSignupsAre400`                              |
| Unknown id                                           | `404`                        | `unknownSignupsAre404`                          |
| Duplicate or malformed rows written directly         | Refused by named constraints | `namedConstraintsHoldWithoutJava`               |
| jose@ and josé@ written directly                     | Two rows                     | `anAccentMakesADifferentAddressOnBothDatabases` |
| A batch with a duplicate                             | Nothing kept                 | `aBatchWithADuplicateLeavesNothing`             |
| 10 spellings at the same moment                      | One `201`, nine `409`        | `tenSpellingsAtOnceMakeOneSignup`               |

## The trap

Plausible but wrong

Assuming case-insensitive uniqueness works the same on both databases.

The trap test uses no Spring at all: plain JDBC on the two real databases, the old table (`email VARCHAR(254) NOT NULL UNIQUE`) created the same way on each, and the same inserts. PostgreSQL keeps both Ashas; MySQL keeps one. MySQL also refuses josé@x.com after jose@x.com, because its default collation ignores accents. The old lookup, `WHERE email = ?`, says "not signed up yet" on PostgreSQL. On the same table, an index on `lower(email)` refuses the second Asha.

While building, each part was undone once. A plain unique index on PostgreSQL turned 3 database tests red; the HTTP tests stayed green, because the Java lookup on `lower(email)` still answered `409` one request at a time. Only the race and the direct inserts showed the missing rule. MySQL's default collation instead of `utf8mb4_bin` turned 1 red (the accent test). Without the `DuplicateKeyException` catch, 2 (the race, on both databases). Comparing `email = ?` in the lookup turned none red: the index still answered `409`.

``` code
package com.taskloom.signups;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.Statement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The first test written for this station, without Spring: the old table, "email VARCHAR(254) UNIQUE", created the
 * same way on both real databases, and the same two inserts. The databases disagree.
 */
class CaseSensitivityTrapTest {

    static final String OLD_TABLE = "CREATE TABLE old_signups (id INT PRIMARY KEY, email VARCHAR(254) NOT NULL UNIQUE)";

    @BeforeAll
    static void start() {
        Databases.POSTGRES.start();
        Databases.MYSQL.start();
    }

    /** The containers are shared with the Spring tests, whose Flyway wants an empty schema: leave none behind. */
    @AfterAll
    static void dropTheOldTable() throws SQLException {
        for (var db : java.util.List.of(Databases.POSTGRES, Databases.MYSQL)) {
            try (Connection c = open(db); Statement s = c.createStatement()) {
                s.execute("DROP TABLE IF EXISTS old_signups");
            }
        }
    }

    static Connection open(org.testcontainers.containers.JdbcDatabaseContainer<?> db) throws SQLException {
        return DriverManager.getConnection(db.getJdbcUrl(), db.getUsername(), db.getPassword());
    }

    /** Creates the old table fresh and inserts the emails in order; returns how many rows went in before one was refused. */
    static int insert(org.testcontainers.containers.JdbcDatabaseContainer<?> db, String... emails) throws SQLException {
        try (Connection c = open(db); Statement s = c.createStatement()) {
            s.execute("DROP TABLE IF EXISTS old_signups");
            s.execute(OLD_TABLE);
            for (int i = 0; i < emails.length; i++) {
                try {
                    s.execute("INSERT INTO old_signups VALUES (" + i + ", '" + emails[i] + "')");
                } catch (SQLException duplicate) {
                    return i;
                }
            }
            return emails.length;
        }
    }

    @Test
    void postgresqlKeepsTwoAshas() throws SQLException {
        assertThat(insert(Databases.POSTGRES, "Asha@x.com", "asha@x.com")).isEqualTo(2);   // two accounts for one person
    }

    @Test
    void mysqlKeepsOne() throws SQLException {
        assertThat(insert(Databases.MYSQL, "Asha@x.com", "asha@x.com")).isEqualTo(1);      // its default collation ignores case
    }

    @Test
    void mysqlAlsoIgnoresAccentsWhichNobodyAskedFor() throws SQLException {
        // utf8mb4_0900_ai_ci: "ai" is accent-insensitive. Two different addresses collide.
        assertThat(insert(Databases.MYSQL, "jose@x.com", "josé@x.com")).isEqualTo(1);
        assertThat(insert(Databases.POSTGRES, "jose@x.com", "josé@x.com")).isEqualTo(2);
    }

    @Test
    void theOldCodeLookedUpWithEqualsSoPostgresMissedTheDuplicateToo() throws SQLException {
        insert(Databases.POSTGRES, "Asha@x.com");
        try (Connection c = open(Databases.POSTGRES); Statement s = c.createStatement()) {
            var found = s.executeQuery("SELECT count(*) FROM old_signups WHERE email = 'asha@x.com'");
            found.next();
            assertThat(found.getInt(1)).isZero();   // "not signed up yet", says the check before the insert
        }
        assertThatThrownBy(() -> {
            try (Connection c = open(Databases.POSTGRES); Statement s = c.createStatement()) {
                s.execute("CREATE UNIQUE INDEX old_signups_lower ON old_signups (lower(email))");
                s.execute("INSERT INTO old_signups VALUES (9, 'asha@x.com')");
            }
        }).hasMessageContaining("old_signups_lower");   // the fix, on the same table: now refused
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
docker compose up -d --wait                       # PostgreSQL on 5432, MySQL on 3306
./mvnw spring-boot:run                            # the API on PostgreSQL, http://localhost:8080
./mvnw spring-boot:run -Dspring-boot.run.profiles=mysql   # or the same API on MySQL
./mvnw test                                       # all 22 tests; starts its own containers
```

**Windows (PowerShell)**

``` code
docker compose up -d --wait
.\mvnw.cmd spring-boot:run
.\mvnw.cmd spring-boot:run "-Dspring-boot.run.profiles=mysql"
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. MySQL takes longer to start than PostgreSQL; the first test run downloads both images.

## Try it yourself

Ask each database what "equal" means:

``` code
docker compose exec postgres psql -U taskloom -d taskloom -c "SELECT 'Asha@x.com' = 'asha@x.com'"
docker compose exec mysql mysql --default-character-set=utf8mb4 -utaskloom -ptaskloom taskloom -e "SELECT 'Asha@x.com' = 'asha@x.com', 'jose@x.com' = 'josé@x.com'"
```

Compare your answers with `docs/captures/equality.txt`, from the build machine. Leave out `--default-character-set=utf8mb4` once: the client then talks latin1 to the server, and the answer about accents changes. That happened while this station was built.

## Troubleshooting

| You see                                                     | Cause                                                                                  | Fix                                                                 |
|-------------------------------------------------------------|----------------------------------------------------------------------------------------|---------------------------------------------------------------------|
| Duplicate accounts on PostgreSQL only                       | A plain `UNIQUE (email)`; PostgreSQL compares exactly.                                 | A unique index on `lower(email)`.                                   |
| MySQL refuses an address that is different                  | The default collation ignores accents (`ai`).                                          | `COLLATE utf8mb4_bin` on the column, plus the `lower(email)` index. |
| `Found non-empty schema(s) ... but no schema history table` | Something created a table before Flyway ran (here: a test).                            | Clean up after tests that create tables by hand.                    |
| Flyway runs the wrong SQL for the database                  | One migrations folder for both.                                                        | `spring.flyway.locations: classpath:db/migration/{vendor}`.         |
| The mysql client gives a different answer from the app      | The client's connection character set (latin1 here) decides the collation of literals. | `--default-character-set=utf8mb4`, as JDBC uses.                    |
| The first test run is slow                                  | MySQL's container takes several seconds to be ready.                                   | The containers are shared, so it happens once per run.              |

## Project layout

``` tree
stations/053-sign-up-emails-on-mysql-and-postgresql/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/taskloom/signups/
│   ├── SignupController.java   ├── SignupDesk.java   └── SignupsApplication.java
├── src/main/resources/
│   ├── application.yaml   ├── application-mysql.yaml
│   └── db/migration/postgresql/V1__signups.sql, db/migration/mysql/V1__signups.sql
├── src/test/java/com/taskloom/signups/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then each database's schema.

#### `src/main/java/com/taskloom/signups/SignupController.java`

Does  
Trims and validates; `Location` on success.

Why  
ASCII emails only, with the reason written down.

Without it  
Lower-casing rules that differ between Java and each database.

#### `src/main/java/com/taskloom/signups/SignupDesk.java`

Does  
Looks up `lower(email)`, inserts, turns a duplicate key into `409`.

Why  
Plain SQL that means the same on both databases.

Without it  
A lookup that misses a duplicate the index then refuses.

- `lower(email) = ?` with a `Locale.ROOT` lower-cased value matches the expression index on both.
- Spring turns both databases' duplicate errors into `DuplicateKeyException`.

#### `src/main/resources/db/migration/postgresql/V1__signups.sql`

Does  
PostgreSQL's schema: an expression index on `lower(email)`.

Why  
PostgreSQL compares exactly by default.

Without it  
Two accounts for one person.

#### `src/main/resources/db/migration/mysql/V1__signups.sql`

Does  
MySQL's schema: an exact column (`utf8mb4_bin`) and a functional index on `lower(email)`.

Why  
The same rule as PostgreSQL, the same name.

Without it  
Accent-insensitive comparison nobody chose.

#### `src/main/resources/application.yaml`

PostgreSQL by default; Flyway reads `db/migration/{vendor}`.

#### `src/main/resources/application-mysql.yaml`

The `mysql` profile: the MySQL connection.

#### `compose.yaml`

Both databases, with health checks.

#### `pom.xml`

Both drivers, both Flyway modules, both Testcontainers modules.

#### `src/main/java/com/taskloom/signups/SignupsApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                                                      | Result |
|---------------|-------------------------------------------------------|-----------------------------------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found              | `PostgresSignupContractTest` (5), `MySqlSignupContractTest` (5) | pass   |
| Every station | Reproduce the failure before the fix                  | `CaseSensitivityTrapTest` (4)                                   | pass   |
| Database      | Rollback and constraint tests against a real database | `PostgresSignupDatabaseTest` (4), `MySqlSignupDatabaseTest` (4) | pass   |

## One test, two databases

The tests are written once, in `SignupContract` and `SignupDatabase`. Four tiny classes run them: each extends one and imports one database. The containers live in `Databases` and start once per run, shared by the Spring tests (through `@ServiceConnection`) and by the trap test (through plain JDBC).

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 and MySQL 8.4 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.signups.CaseSensitivityTrapTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.signups.MySqlSignupContractTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.signups.PostgresSignupContractTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.signups.MySqlSignupDatabaseTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.signups.PostgresSignupDatabaseTest
[INFO] Tests run: 22, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/taskloom/signups/SignupContract.java`

The HTTP contract, written once.

#### `src/test/java/com/taskloom/signups/SignupDatabase.java`

Constraints, accents, a rollback and a race, written once.

#### `src/test/java/com/taskloom/signups/PostgresSignupContractTest.java`

The contract on PostgreSQL. Its three siblings are the same three lines for the other combinations.

#### `src/test/java/com/taskloom/signups/Databases.java`

The two shared containers and their `@ServiceConnection` configurations.

#### `src/test/java/com/taskloom/signups/ApiTest.java`

Shared setup: an empty table before each test; parallel calls.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/taskloom/signups/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=FindByEmailChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 22 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 24 tests pass (22 station tests and 2 challenge tests).

Challenge 1 · Beginner-friendly · about 15 minutes

## Find by email

Add `GET /signups?email=…`: the sign-up for that address however it is typed, or `404`. The test runs on PostgreSQL; switch its `@Import` to try MySQL.

**Done when:** the test in `FindByEmailChallengeTest` passes.

Hints

- `SignupDesk.findByEmail` already exists.
- Trim before looking up.

#### `challenge/FindByEmailChallengeTest.java`

``` code
package com.taskloom.signups;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /signups?email=... finds a sign-up however the email is typed (case, spaces around it), and is 404
 * when there is none. Runs on PostgreSQL; change the @Import to Databases.MySql.class to try MySQL.
 */
@Import(Databases.Postgres.class)
class FindByEmailChallengeTest extends ApiTest {

    @Test
    void foundIgnoringCase() throws Exception {
        signUp("Asha.Verma@Example.in");
        mvc.perform(get("/signups").param("email", " ASHA.VERMA@example.IN ")).andExpect(status().isOk())
                .andExpect(jsonPath("$.email").value("Asha.Verma@Example.in"));
        mvc.perform(get("/signups").param("email", "rohan@example.in")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 25 minutes

## Change an email

Add `PATCH /signups/{id}/email`. Someone else's address in any case is `409`; changing the case of your own is fine. The test runs on MySQL.

**Done when:** the test in `ChangeEmailChallengeTest` passes.

Hints

- The lookup finds a holder: a conflict only if it is another row.
- The unique index still guards the race between the check and the update.

#### `challenge/ChangeEmailChallengeTest.java`

``` code
package com.taskloom.signups;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: PATCH /signups/{id}/email {"email": "..."} changes the address. Someone else's address, in any case,
 * is 409; your own in another case is fine (Asha@x.com to asha@x.com). Unknown id: 404. Runs on MySQL.
 */
@Import(Databases.MySql.class)
class ChangeEmailChallengeTest extends ApiTest {

    ResultActions change(String url, String email) throws Exception {
        return mvc.perform(patch(url + "/email").contentType(MediaType.APPLICATION_JSON).content("{\"email\":\"" + email + "\"}"));
    }

    @Test
    void anAddressBelongsToOneSignup() throws Exception {
        String asha = signUp("Asha@x.com").andReturn().getResponse().getHeader("Location");
        signUp("rohan@x.com");
        change(asha, "asha@x.com").andExpect(status().isOk()).andExpect(jsonPath("$.email").value("asha@x.com"));
        change(asha, "ROHAN@x.com").andExpect(status().isConflict());
        change(asha, "asha.verma@x.com").andExpect(status().isOk());
        change("/signups/999999", "new@x.com").andExpect(status().isNotFound());
        change(asha, "not-an-email").andExpect(status().isBadRequest());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Is two databases worth it?

List what Taskloom pays for supporting both: two migrations per change, every test twice, features one database lacks. Then list what it gains. When would you drop one, and how would you move its customers?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test on both real databases, with the old table.
2.  Write the rule in words: equal after lower-casing, nothing else.
3.  Translate it into each database's SQL, under one constraint name.
4.  Write the tests once and run them on both.

## Design alternatives and trade-offs

| Approach                                                       | What it costs                                                    | Verdict                   |
|----------------------------------------------------------------|------------------------------------------------------------------|---------------------------|
| Expression index on `lower(email)` on both; exact MySQL column | Two migrations; queries must use `lower(email)`.                 | Chosen                    |
| Plain `UNIQUE (email)` on both                                 | Different answers per database.                                  | The trap                  |
| Store the email lower-cased                                    | One plain unique index; the address is no longer shown as typed. | Simpler, loses the typing |
| PostgreSQL `citext` or a nondeterministic collation            | Neat on PostgreSQL; nothing like it on MySQL.                    | One database only         |
| Check uniqueness in Java only                                  | Two requests at once both pass.                                  | No                        |

## Database design

| Database   | Column                                             | Constraints                                                       |
|------------|----------------------------------------------------|-------------------------------------------------------------------|
| PostgreSQL | `email VARCHAR(254)` (exact comparison by default) | `signups_email_unique` on `lower(email)`, `signups_email_shape`   |
| MySQL      | `email VARCHAR(254) COLLATE utf8mb4_bin`           | `signups_email_unique` on `(lower(email))`, `signups_email_shape` |

``` code
-- PostgreSQL compares text case-sensitively: a plain UNIQUE (email) lets Asha@x.com and asha@x.com both in.
CREATE TABLE signups (
    id         BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    email      VARCHAR(254) NOT NULL,
    name       VARCHAR(80)  NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT signups_email_shape CHECK (email LIKE '_%@_%' AND email NOT LIKE '% %')
);

-- Unique on the lower-cased email: one person, one sign-up, however they type it.
CREATE UNIQUE INDEX signups_email_unique ON signups (lower(email));
```

``` code
-- MySQL's default collation (utf8mb4_0900_ai_ci) ignores case AND accents: jose@x.com and josé@x.com would be "equal".
-- utf8mb4_bin compares exactly, like PostgreSQL; the index on lower(email) then adds case-insensitivity, and nothing else.
CREATE TABLE signups (
    id         BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    email      VARCHAR(254) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
    name       VARCHAR(80)  NOT NULL,
    created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT signups_email_shape CHECK (email LIKE '_%@_%' AND email NOT LIKE '% %')
);

-- A functional index (MySQL 8.0.13+): the same rule as PostgreSQL's, under the same name.
CREATE UNIQUE INDEX signups_email_unique ON signups ((lower(email)));
```

# 3 · Go deeper: Production

Existing duplicates  
On a live PostgreSQL database, creating the new index fails while two Ashas exist. Find them first (`GROUP BY lower(email) HAVING count(*) > 1`), merge the accounts with the customers, then add the index.

Collations are settings  
MySQL's server, database, table and column can each have a collation. Write the one you rely on into the column, not into a server setting someone may change.

Upgrades  
MySQL changed its default collation in version 8.0. A rule inherited from a default can change with an upgrade; a rule written in the schema does not.

Index use  
An expression index is only used when the query has the same expression. `WHERE email = ?` ignores it.

# 3 · Go deeper: Interview

## Interview takeaways

Why can the same UNIQUE column behave differently on MySQL and PostgreSQL?

Uniqueness uses the column's comparison rules. MySQL's default utf8mb4 collation is case- and accent-insensitive; PostgreSQL's default comparison is exact.

How do you make email uniqueness case-insensitive in PostgreSQL?

A unique expression index on lower(email), and queries that compare lower(email). citext is another option, PostgreSQL-only.

What does utf8mb4_0900_ai_ci mean?

utf8mb4 is the character set; 0900 is the Unicode collation algorithm version; ai is accent-insensitive; ci is case-insensitive.

Why run the tests on both databases?

Because the behaviour that matters lives in the database. A test on one says nothing about the other; Testcontainers makes running both cheap.

Where does portability end?

At SQL syntax (identity columns, functional indexes), collations, error messages and features. Keep the rule the same, and let each schema say it in its own SQL.

## Self-check rubric

| Area        | Meets the bar                         | Above the bar                                                     |
|-------------|---------------------------------------|-------------------------------------------------------------------|
| Correctness | All 22 tests pass, on both databases. | You explained why the HTTP tests stayed green with a plain index. |
| Databases   | Collations explained.                 | You can read a MySQL collation name.                              |
| Schema      | Expression index on both.             | A migration plan for existing duplicates.                         |
| Testing     | Same tests, two databases.            | Shared containers, one start per run.                             |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any text that must be unique:

- What does "the same" mean here, in words?
- Which collation does each database use for this column, and is it written in the schema?
- Does every query compare the same expression the index is on?
- Is the rule tested on every database the product supports?
