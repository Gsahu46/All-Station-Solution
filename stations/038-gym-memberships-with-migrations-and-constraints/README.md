# Station 038 · Gym memberships with migrations and constraints

Foundations · 0–1 years · Core · Fitness · Types: Database

Spring Boot 4.1.1 · Java 25 · Flyway versioned migrations · PostgreSQL 17 constraints: PK, FK, UNIQUE, CHECK, EXCLUDE · JdbcClient · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Members, plans and prices are demo data, not FitNest's. A membership is a record; no payment is taken.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 12 tests.

# 1 · Understand

## The problem in real life

1.  **Rules in Java only**

    The app refuses a duplicate phone and a membership that ends before it starts. The database itself only knows primary keys.

2.  **Another writer**

    The front desk's spreadsheet sync writes straight to the database. Asha is now two members, "98765 43210" and "+91 9876543210", and one membership ends in October but starts in November.

3.  **The fix**

    A new migration moves the rules into the database, named. Now every writer meets them, and the app turns a refusal into a clear 409.

A rule that only one program knows is a suggestion. A constraint is a rule.

## What are we building?

`POST /members` registers a member by phone; `POST /members/{id}/memberships` sells a monthly, quarterly or annual membership. The database refuses a second member with the same phone, a membership that ends before it starts, and two memberships on the same day.

## An everyday analogy

A gym's turnstile. The receptionist checks your card, but the turnstile checks it again, and it also stops anyone who climbs in through the side door.

## How it works in 4 steps

1.  **At startup**, Flyway applies any migration the database has not seen yet, in version order.
2.  **Java checks the shape** of a request and writes the phone in one form.
3.  **The database checks the rules** on the insert.
4.  **A refusal's constraint name** decides the answer: duplicate phone or overlap, `409`.

Check yourself: why not ask "is this phone taken?" before inserting?

Two requests can both ask at the same moment, both hear "no", and both insert. The unique constraint lets only one of them win, every time.

## What this station is not

- **No payments.** A membership is a record.
- **No member login.** The desk registers members.
- **No zero-downtime migration.** Adding constraints to a large live table is challenge 3.

## Key terms

| Term              | Simple meaning                                                                               | Everyday example                                                        | In this project                 |
|-------------------|----------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|---------------------------------|
| **Migration**     | A numbered SQL file that changes the database from one version to the next.                  | Numbered amendments to a rule book; old ones are never rewritten.       | `V2__plans_and_constraints.sql` |
| **Constraint**    | A rule the database checks on every write, from any program.                                 | A turnstile: it does not care who is pushing.                           | `members_phone_unique`          |
| **Foreign key**   | A column that must point at an existing row elsewhere.                                       | A locker number that must exist.                                        | `memberships_member_fk`         |
| **CHECK**         | A condition every row must meet.                                                             | "End date on or after start date" printed on the form.                  | `memberships_dates_order`       |
| **EXCLUDE**       | No two rows may conflict, for a meaning of "conflict" you choose, such as overlapping dates. | One locker, one member per day.                                         | `memberships_no_overlap`        |
| **Normalisation** | Each fact stored once, in the table it belongs to.                                           | A price list on the wall, not a price written by hand on every receipt. | the `plans` table               |

# 2 · Build: Spec

## Business problem

**FitNest** (a fictional gym chain) found two members sharing one phone number and a membership that ends before it starts. The schema allowed both.

## Acceptance criteria

1.  **Given** `+91 98765-43210`, **then** the member is stored with `9876543210`; `098765 43210` for another member is `409`.
2.  **Given** a quarterly membership from 15 November 2026, **then** it ends on 14 February 2027 and costs ₹3,999.00.
3.  **Given** a membership covering any of those days, **then** `409`; one starting on 15 February, `201`.
4.  **Given** any writer at all, **then** a duplicate phone, a phone in another form, inverted dates, an unknown member or plan, or a zero price are refused by named constraints.
5.  **Given** an old database with bad rows, **then** the V2 migration fails, names the rule, and changes nothing until the rows are fixed.
6.  **Given** an unknown member, `404`; an unknown plan, `422`; a bad phone or date, `400`.

## Requirements

- Schema changes are new versioned migrations; released ones are never edited.
- Every business rule in Java is also a named database constraint, with a test that bypasses Java.
- Phones are stored in one form, so `UNIQUE` sees duplicates.
- Money in integer paise.

## Learning objectives

- Evolve a schema with Flyway versioned migrations.
- Use primary, foreign, unique, check and exclusion constraints.
- Normalise a repeated fact into its own table, and know when a copy is a fact of its own.
- Write SQL with `JdbcClient`, and map a constraint violation to `409`.

# 2 · Build: API contract

## Endpoints

| Method | Path                        | Body                                                                |
|--------|-----------------------------|---------------------------------------------------------------------|
| `POST` | `/members`                  | `{"name", "phone"}`                                                 |
| `POST` | `/members/{id}/memberships` | `{"planCode", "startsOn"}`: MONTHLY, QUARTERLY or ANNUAL, any case. |

## Status codes

| Status | When                                                                |
|--------|---------------------------------------------------------------------|
| 201    | A member or membership was created                                  |
| 400    | A bad phone, a blank name or plan, a date that does not exist       |
| 404    | No such member                                                      |
| 409    | The phone is already registered, or the membership overlaps another |
| 422    | A plan FitNest does not sell                                        |

## Captured examples

Captured with curl from the running app on 15 Oct 2026, in this order, against one fresh database. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: a phone with +91 and a dash

**Why:** stored as 10 digits, the one form the database accepts.

Request

``` code
POST /members HTTP/1.1
Content-Type: application/json

{
  "name": "Asha Verma",
  "phone": "+91 98765-43210"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 49

{
  "id": 1,
  "name": "Asha Verma",
  "phone": "9876543210"
}
```

### Case 2: the same number with a leading 0

**Why:** the same 10 digits: `members_phone_unique` refuses it.

Request

``` code
POST /members HTTP/1.1
Content-Type: application/json

{
  "name": "Asha V",
  "phone": "098765 43210"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Another member already has this phone number.",
  "instance": "/members",
  "status": 409,
  "title": "Phone already registered"
}
```

### Case 3: 12345

**Why:** `400`, before the database.

Request

``` code
POST /members HTTP/1.1
Content-Type: application/json

{
  "name": "Ravi Iyer",
  "phone": "12345"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "phone must be a 10-digit Indian mobile number.",
  "instance": "/members",
  "status": 400,
  "title": "Invalid phone"
}
```

### Case 4: quarterly from 15 November

**Why:** ends the day before 15 February; the plan's price is stored on the membership.

Request

``` code
POST /members/1/memberships HTTP/1.1
Content-Type: application/json

{
  "planCode": "quarterly",
  "startsOn": "2026-11-15"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 110

{
  "id": 1,
  "memberId": 1,
  "planCode": "QUARTERLY",
  "startsOn": "2026-11-15",
  "endsOn": "2027-02-14",
  "pricePaise": 399900
}
```

### Case 5: monthly from 31 January

**Why:** covers days already covered: `memberships_no_overlap`.

Request

``` code
POST /members/1/memberships HTTP/1.1
Content-Type: application/json

{
  "planCode": "MONTHLY",
  "startsOn": "2027-01-31"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "This member already has a membership covering some of these days.",
  "instance": "/members/1/memberships",
  "status": 409,
  "title": "Overlapping membership"
}
```

### Case 6: monthly from 15 February

**Why:** starts the day after the last one ends.

Request

``` code
POST /members/1/memberships HTTP/1.1
Content-Type: application/json

{
  "planCode": "MONTHLY",
  "startsOn": "2027-02-15"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 108

{
  "id": 3,
  "memberId": 1,
  "planCode": "MONTHLY",
  "startsOn": "2027-02-15",
  "endsOn": "2027-03-14",
  "pricePaise": 149900
}
```

### Case 7: WEEKLY

**Why:** `422`.

Request

``` code
POST /members/1/memberships HTTP/1.1
Content-Type: application/json

{
  "planCode": "WEEKLY",
  "startsOn": "2026-11-01"
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "Plans are MONTHLY, QUARTERLY and ANNUAL.",
  "instance": "/members/1/memberships",
  "status": 422,
  "title": "Unknown plan"
}
```

### Case 8: member 99

**Why:** `404`.

Request

``` code
POST /members/99/memberships HTTP/1.1
Content-Type: application/json

{
  "planCode": "MONTHLY",
  "startsOn": "2026-11-01"
}
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No member 99.",
  "instance": "/members/99/memberships",
  "status": 404,
  "title": "Member not found"
}
```

## The database behind them

Queried with psql after the captures. Flyway's record of what ran (`docs/captures/flyway-history.txt`):

``` code
 version |       description       | success 
---------+-------------------------+---------
 1       | members and memberships | t
 2       | plans and constraints   | t
(2 rows)
```

Every constraint on the three tables (`docs/captures/constraints.txt`):

``` code
  on_table   |      constraint_name       |    kind     
-------------+----------------------------+-------------
 members     | members_phone_digits       | check
 members     | members_phone_unique       | unique
 members     | members_pkey               | primary key
 memberships | memberships_dates_order    | check
 memberships | memberships_member_fk      | foreign key
 memberships | memberships_no_overlap     | exclude
 memberships | memberships_pkey           | primary key
 memberships | memberships_plan_fk        | foreign key
 memberships | memberships_price_positive | check
 plans       | plans_months_range         | check
 plans       | plans_pkey                 | primary key
 plans       | plans_price_positive       | check
(12 rows)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                                      | What happens                                       | Proved by                                                        |
|---------------------------------------------------------------------------|----------------------------------------------------|------------------------------------------------------------------|
| Another writer, version 1 schema                                          | Duplicate phone and inverted dates stored          | `JavaOnlyRulesTrapTest`                                          |
| The same writer, version 2 schema                                         | Refused by name                                    | `JavaOnlyRulesTrapTest`                                          |
| Phone format, unknown member or plan, zero price                          | Refused by named constraints                       | `everyRuleIsANamedConstraint`                                    |
| Overlap; back-to-back; another member's same days                         | Refused; allowed; allowed                          | `overlappingMembershipsAreRefusedButBackToBackOnesAreFine`       |
| A member and a bad membership in one transaction                          | Neither is kept                                    | `aFailureInsideATransactionTakesTheNewMemberWithIt`              |
| V2 run on a database with bad rows                                        | Fails by name, rolled back, succeeds after the fix | `addingConstraintsToBadDataFailsTheMigrationUntilTheDataIsFixed` |
| Through HTTP: duplicate phone, overlap, unknown member or plan, bad input | `409`, `409`, `404`, `422`, `400`                  | `MembershipContractTest`                                         |

## The trap

Plausible but wrong

Enforcing rules only in Java; another writer inserts invalid rows.

The test migrates a separate schema to version 1, as it shipped. Plain SQL, standing in for the spreadsheet sync, stores Asha twice under one phone, and a membership that ends a month before it starts. The same statements against the version 2 schema are refused by `members_phone_unique`, `members_phone_digits` and `memberships_dates_order`. While building, each fix was undone once. Dropping the unique phone turned 3 tests red, and dropping the overlap rule 2. Not normalising phones in the migration turned 1 red, not mapping a duplicate phone to 409 1, and not mapping an overlap 1.

``` code
package com.fitnest.members;

import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The first test written for this station. Schema "v1_only" holds the database as version 1 shipped (rules in Java
 * only); another writer, here plain SQL, stores what the Java code would have refused. The app's schema, at version 2,
 * refuses the same rows by name.
 */
class JavaOnlyRulesTrapTest extends ApiTest {

    @BeforeEach
    void versionOneInItsOwnSchema() {
        jdbc.sql("DROP SCHEMA IF EXISTS v1_only CASCADE").update();
        Flyway.configure().dataSource(dataSource).schemas("v1_only").target("1").load().migrate();
    }

    @Test
    void versionOneLetsAnotherWriterStoreTwoMembersWithOnePhone() {
        jdbc.sql("INSERT INTO v1_only.members (name, phone) VALUES ('Asha Verma', '98765 43210'), ('Asha V', '+91 9876543210')").update();
        assertThat(jdbc.sql("SELECT count(*) FROM v1_only.members").query(Long.class).single()).isEqualTo(2);

        jdbc.sql("INSERT INTO members (name, phone) VALUES ('Asha Verma', '9876543210')").update();
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO members (name, phone) VALUES ('Asha V', '9876543210')").update())
                .hasMessageContaining("members_phone_unique");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO members (name, phone) VALUES ('Asha V', '+91 9876543210')").update())
                .hasMessageContaining("members_phone_digits");   // only the one stored form is allowed, so UNIQUE can see duplicates
    }

    @Test
    void versionOneLetsAMembershipEndBeforeItStarts() {
        jdbc.sql("INSERT INTO v1_only.memberships (member_id, plan, starts_on, ends_on, price_paise) VALUES (1, 'Monthly', DATE '2026-11-01', DATE '2026-10-01', 149900)").update();
        assertThat(jdbc.sql("SELECT count(*) FROM v1_only.memberships WHERE ends_on < starts_on").query(Long.class).single()).isEqualTo(1);

        long member = jdbc.sql("INSERT INTO members (name, phone) VALUES ('Ravi Iyer', '9123456780') RETURNING id").query(Long.class).single();
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO memberships (member_id, plan_code, starts_on, ends_on, price_paise) VALUES (?, 'MONTHLY', DATE '2026-11-01', DATE '2026-10-01', 149900)")
                .param(member).update())
                .hasMessageContaining("memberships_dates_order");
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
./mvnw spring-boot:run      # the API on http://localhost:8080; Flyway applies V1 and V2 first
./mvnw test                 # all 12 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Be the other writer. With the app running, insert a membership that ends before it starts, straight into the database:

``` code
docker compose exec postgres psql -U fitnest -d fitnest -c "INSERT INTO members (name, phone) VALUES ('Desk test', '9000000001')"
docker compose exec postgres psql -U fitnest -d fitnest -c "INSERT INTO memberships (member_id, plan_code, starts_on, ends_on, price_paise) SELECT id, 'MONTHLY', DATE '2026-11-30', DATE '2026-11-01', 149900 FROM members WHERE phone = '9000000001'"
```

Read the constraint name in the error. Then look at what Flyway recorded: `SELECT * FROM flyway_schema_history`.

## Troubleshooting

| You see                                                                   | Cause                                  | Fix                                                                                                                                         |
|---------------------------------------------------------------------------|----------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------|
| `Validate failed: Migration checksum mismatch for migration version 1`    | A released migration was edited.       | Put it back as it was, and make the change in a new version.                                                                                |
| `could not create unique index "members_phone_unique"` while migrating    | Existing rows break the new rule.      | Find them (`SELECT phone, count(*) FROM members GROUP BY phone HAVING count(*) > 1`), fix them with the business, then start the app again. |
| `data type bigint has no default operator class for access method "gist"` | The `btree_gist` extension is missing. | V2 creates it; on a managed database you may need an administrator to allow it.                                                             |
| `Could not find a valid Docker environment`                               | Docker is not running.                 | Start Docker, then run the tests again.                                                                                                     |

## Project layout

``` tree
stations/038-gym-memberships-with-migrations-and-constraints/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/fitnest/members/
│   ├── MemberController.java   ├── MemberStore.java   ├── Phones.java   └── MembersApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__members_and_memberships.sql, V2__plans_and_constraints.sql
├── src/test/java/com/fitnest/members/   (see Tests)
├── challenge/                Practice tests; solutions (including new migrations) ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the migrations behind it.

#### `src/main/java/com/fitnest/members/MemberController.java`

Does  
Validates requests, normalises the phone, and turns a named constraint violation into a `409`.

Why  
Java gives the friendly message; the database gives the guarantee.

Without it  
Asking "is it taken?" first: two requests can both hear "no".

#### `src/main/java/com/fitnest/members/MemberStore.java`

Does  
SQL with `JdbcClient`.

Why  
Named parameters, `RETURNING` for the new row, and records mapped by column name.

Without it  
Hand-written `ResultSet` loops for every query.

#### `src/main/java/com/fitnest/members/Phones.java`

Does  
Writes a phone in one form: 10 digits.

Why  
`UNIQUE` compares exact text, so one number written two ways would slip past it.

Without it  
"98765 43210" and "+91 9876543210" stored as two members.

#### `src/main/resources/db/migration/V1__members_and_memberships.sql`

Does  
The schema as version 1 shipped.

Why  
Kept unchanged: databases already at version 1 must replay history exactly.

Without it  
Editing it breaks Flyway's checksum on every database that already ran it.

#### `src/main/resources/db/migration/V2__plans_and_constraints.sql`

Does  
Moves every rule into the database, and plans into their own table.

Why  
One transaction: if old rows break a new rule, nothing changes and the error names the rule.

Without it  
Rules that only the Java code knows.

- Phones are rewritten into one form before `UNIQUE` is added.
- The `EXCLUDE` constraint is its own statement, after the dates check; see the Design tab.

#### `src/main/resources/application.yaml`

The database and strict JSON.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/fitnest/members/MembersApplication.java`

Entry point. Flyway runs the migrations before the app takes requests.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                   | Result |
|---------------|-------------------------------------------------------|------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found              | `MembershipContractTest` (5) | pass   |
| Every station | Reproduce the failure before the fix                  | `JavaOnlyRulesTrapTest` (2)  | pass   |
| Database      | Rollback and constraint tests against a real database | `MembershipDatabaseTest` (5) | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.fitnest.members.MembershipDatabaseTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.fitnest.members.JavaOnlyRulesTrapTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.fitnest.members.MembershipContractTest
[INFO] Tests run: 12, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/fitnest/members/JavaOnlyRulesTrapTest.java`

Written first: version 1 in its own schema lets another writer store what Java refuses.

#### `src/test/java/com/fitnest/members/MembershipDatabaseTest.java`

Every named constraint, overlap, a rollback, and the V2 migration meeting bad data.

#### `src/test/java/com/fitnest/members/MembershipContractTest.java`

Members and memberships through HTTP, and every refusal.

#### `src/test/java/com/fitnest/members/ApiTest.java`

Shared setup: empty tables before each test.

#### `src/test/java/com/fitnest/members/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/fitnest/members/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=MemberEmailChallengeTest` (Docker must be running).
3.  Add a new migration file and change the code until it passes, then run `./mvnw test` to check the other 12 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in (two Java files and two new migrations), all 16 tests pass (12 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## An email, unique in any case

Members may give an email. Add it in `V3`, never by editing V1 or V2: optional, unique whatever the letter case, enforced by the database; a second member with the same email is `409`.

**Done when:** both tests in `MemberEmailChallengeTest` pass.

Hints

- A unique index on `lower(email)` treats ASHA@ and asha@ as the same.
- NULLs are never equal to each other, so many members can have no email.

#### `challenge/MemberEmailChallengeTest.java`

``` code
package com.fitnest.members;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: members may give an email. Add it with a new migration, V3 (never by editing V1 or V2): an optional
 * column, unique in any letter case, enforced by the database. A second member with the same email is a 409.
 */
class MemberEmailChallengeTest extends ApiTest {

    void joinWithEmail(String phone, String email, int status) throws Exception {
        mvc.perform(post("/members").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"Asha\",\"phone\":\"%s\",\"email\":\"%s\"}".formatted(phone, email)))
                .andExpect(status().is(status));
    }

    @Test
    void anEmailIsStoredAndUniqueInAnyCase() throws Exception {
        joinWithEmail("9876543210", "asha@example.com", 201);
        joinWithEmail("9123456780", "ASHA@Example.com", 409);
        assertThat(count("members")).isEqualTo(1);
    }

    @Test
    void emailIsOptionalAndTheSchemaIsAtVersionThree() throws Exception {
        join("Ravi", "9123456780").andExpect(status().isCreated()).andExpect(jsonPath("$.email").doesNotExist());
        join("Meena", "9123456781").andExpect(status().isCreated());   // two members without an email are fine
        assertThat(jdbc.sql("SELECT version FROM flyway_schema_history WHERE success ORDER BY installed_rank").query(String.class).list())
                .contains("3");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Freeze a membership

`POST /memberships/{id}/freeze` with `{"days": n}` moves the end n days later, up to 30 frozen days in all (a Java check and a constraint in `V4`). A freeze that runs into the next membership is refused by the overlap rule you already have.

**Done when:** both tests in `FreezeChallengeTest` pass.

Hints

- One `UPDATE … RETURNING` moves the end and adds the days.
- An `EXCLUDE` constraint is checked on updates too: nothing new is needed for the overlap.

#### `challenge/FreezeChallengeTest.java`

``` code
package com.fitnest.members;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: POST /memberships/{id}/freeze {"days": n} pauses a membership: its end moves n days later. At most 30
 * frozen days per membership (a Java check for the message, and memberships_freeze_limit in a new migration). A freeze
 * that would run into the member's next membership is refused by the overlap rule that already exists: 409.
 */
class FreezeChallengeTest extends ApiTest {

    ResultActions freeze(long membershipId, int days) throws Exception {
        return mvc.perform(post("/memberships/{id}/freeze", membershipId).contentType(MediaType.APPLICATION_JSON).content("{\"days\":" + days + "}"));
    }

    @Test
    void aFreezeMovesTheEndUpToThirtyDaysInAll() throws Exception {
        join("Asha", "9876543210");
        buy(1, "MONTHLY", "2026-11-01");
        freeze(1, 10).andExpect(status().isOk()).andExpect(jsonPath("$.endsOn").value("2026-12-10")).andExpect(jsonPath("$.frozenDays").value(10));
        freeze(1, 25).andExpect(status().isUnprocessableContent());
        freeze(1, 20).andExpect(status().isOk()).andExpect(jsonPath("$.endsOn").value("2026-12-30"));
        assertThatThrownBy(() -> jdbc.sql("UPDATE memberships SET frozen_days = 31 WHERE id = 1").update())
                .hasMessageContaining("memberships_freeze_limit");
    }

    @Test
    void aFreezeCannotRunIntoTheNextMembership() throws Exception {
        join("Asha", "9876543210");
        buy(1, "MONTHLY", "2026-11-01");
        buy(1, "MONTHLY", "2026-12-01");
        freeze(1, 1).andExpect(status().isConflict());
        freeze(99, 1).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## A constraint on a table with a crore rows

Adding `UNIQUE` or `CHECK` to a huge live table scans it while holding a lock. Find out what `CHECK … NOT VALID` followed by `VALIDATE CONSTRAINT`, and `CREATE UNIQUE INDEX CONCURRENTLY`, change. Then plan V2 as several migrations that a busy gym chain could run without downtime, and say what happens to bad rows found halfway.

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test against version 1, in a schema of its own.
2.  Write V2: the plans table, phone clean-up, then each rule as a named constraint.
3.  Test each constraint with plain SQL, and V2 against a database with bad rows.
4.  Write the API with `JdbcClient`, mapping constraint names to `409`.

## Normalisation, briefly

| Form | Rule                                         | Here                                                                                          |
|------|----------------------------------------------|-----------------------------------------------------------------------------------------------|
| 1NF  | One value per column, no repeating groups.   | One phone per member row, not a list of phones in one column.                                 |
| 2NF  | Every column depends on the whole key.       | Tables have single-column keys here, so this holds.                                           |
| 3NF  | No column depends on another non-key column. | In V1, a membership's plan name decided its length and list price. V2 moves those to `plans`. |

The membership keeps `price_paise` on purpose. It is what that member paid that day, a fact about the sale. If the plan's price changes next year, past memberships must not change with it.

## Design alternatives and trade-offs

| Approach                                 | What it costs                                      | Verdict                 |
|------------------------------------------|----------------------------------------------------|-------------------------|
| Named constraints + friendly Java checks | Each rule written twice, in SQL and in Java.       | Chosen                  |
| Java checks only                         | Any other writer ignores them.                     | The trap                |
| Check first, then insert                 | Two requests race past the check.                  | A race                  |
| Triggers for the overlap rule            | Hidden logic, easy to get wrong under concurrency. | When no constraint fits |
| Editing V1 instead of adding V2          | Every database already at V1 fails its checksum.   | Never                   |

## Database design

| Table         | Key and constraints                                                                                                                                                         | Why                                                                                            |
|---------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|
| `members`     | Identity PK. `members_phone_digits`, `members_phone_unique`.                                                                                                                | One member per phone, in one stored form.                                                      |
| `plans`       | PK `code`. Months 1 to 24, price \> 0.                                                                                                                                      | Each plan's facts stored once.                                                                 |
| `memberships` | Identity PK. `memberships_member_fk`, `memberships_plan_fk`, `memberships_dates_order`, `memberships_price_positive`, `memberships_no_overlap` (EXCLUDE with `btree_gist`). | No orphan, no unknown plan, no impossible dates, no two memberships on one day for one member. |

**Order inside V2 matters.** Phones are rewritten into one form before `UNIQUE` is added. The `EXCLUDE` constraint is a separate `ALTER`, after the dates check. This was found while building: in one `ALTER`, building its index runs `daterange()` on a row that ends before it starts, and fails with "range lower bound must be less than or equal to range upper bound", which names no rule. As a separate statement, such a row is refused first by `memberships_dates_order`, by name.

``` code
-- Version 2: the rules move into the database, named, so every writer meets them.
-- Runs in one transaction (PostgreSQL DDL is transactional): if existing rows break a new rule, nothing changes and
-- the migration fails, naming the constraint. Fix the rows (see the runbook query in the station), then run it again.

-- Plans get their own table (3NF): a plan's name, length and list price depend on the plan, not on each membership.
CREATE TABLE plans (
    code        VARCHAR(20)  PRIMARY KEY,
    name        VARCHAR(40)  NOT NULL,
    months      SMALLINT     NOT NULL,
    price_paise BIGINT       NOT NULL,
    CONSTRAINT plans_months_range   CHECK (months BETWEEN 1 AND 24),
    CONSTRAINT plans_price_positive CHECK (price_paise > 0)
);
INSERT INTO plans (code, name, months, price_paise) VALUES
    ('MONTHLY', 'Monthly', 1, 149900),
    ('QUARTERLY', 'Quarterly', 3, 399900),
    ('ANNUAL', 'Annual', 12, 1199900);

-- Phones are stored in one form, 10 digits, so "98765 43210" and "+91 9876543210" are the same number to UNIQUE.
UPDATE members SET phone = right(regexp_replace(phone, '[^0-9]', '', 'g'), 10);
ALTER TABLE members
    ADD CONSTRAINT members_phone_digits CHECK (phone ~ '^[6-9][0-9]{9}$'),
    ADD CONSTRAINT members_phone_unique UNIQUE (phone);

-- Memberships point at a plan by code. The price stays on the membership: it is what this member paid that day,
-- a fact about the sale, not a copy of the plan's current price.
ALTER TABLE memberships ADD COLUMN plan_code VARCHAR(20);
UPDATE memberships SET plan_code = upper(trim(plan));
ALTER TABLE memberships ALTER COLUMN plan_code SET NOT NULL, DROP COLUMN plan;

CREATE EXTENSION IF NOT EXISTS btree_gist;   -- lets one EXCLUDE constraint mix "=" on a number with "&&" on dates
ALTER TABLE memberships
    ADD CONSTRAINT memberships_member_fk   FOREIGN KEY (member_id) REFERENCES members (id),
    ADD CONSTRAINT memberships_plan_fk     FOREIGN KEY (plan_code) REFERENCES plans (code),
    ADD CONSTRAINT memberships_dates_order CHECK (ends_on >= starts_on),
    ADD CONSTRAINT memberships_price_positive CHECK (price_paise > 0);
-- A statement of its own, after the dates check: in one ALTER, building this index runs daterange() on a row that ends
-- before it starts and fails with "range lower bound must be less than or equal to range upper bound", which names no
-- rule. Separately, such a row is refused by memberships_dates_order first, by name.
-- One member, no two memberships covering the same day.
ALTER TABLE memberships
    ADD CONSTRAINT memberships_no_overlap EXCLUDE USING gist (member_id WITH =, daterange(starts_on, ends_on, '[]') WITH &&);
```

# 3 · Go deeper: Production

Migrations at startup  
With several app instances starting together, Flyway's lock lets one migrate and the others wait. Large migrations are better run as a separate step before the deploy.

Bad data first  
Before adding a rule to a live table, query for rows that break it, and decide with the business what they mean. A migration that deletes "duplicates" can delete a real customer.

Locks  
Adding constraints locks the table while existing rows are checked; at scale, see challenge 3.

Extensions  
`btree_gist` ships with PostgreSQL, but managed databases may need it allowed by an administrator.

# 3 · Go deeper: Interview

## Interview takeaways

Why put business rules in database constraints if Java already checks them?

Java protects one program. Constraints protect the data from every writer (scripts, other services, manual fixes, future bugs), and they are race-free.

Why must you never edit a released Flyway migration?

Flyway stores each migration's checksum. Databases that already ran it would fail validation, and databases that run it fresh would differ from those that did not. Change things in a new version.

What does an EXCLUDE constraint do?

It forbids two rows that conflict under the operators you give, for example the same member (=) with overlapping date ranges (&&). UNIQUE is the special case where the operator is equality.

How do you turn a constraint violation into a 409?

Catch the data-integrity exception, check which named constraint failed, and map known business rules to 409 with a clear message; anything unexpected stays an error.

What is third normal form, simply?

Every non-key column describes the key, the whole key, and nothing but the key. A plan's price belongs with the plan, not repeated on each membership, unless the copy is a fact of its own, such as what was paid.

## Self-check rubric

| Area        | Meets the bar              | Above the bar                                               |
|-------------|----------------------------|-------------------------------------------------------------|
| Correctness | All 12 tests pass.         | You broke a constraint by hand with psql and read the name. |
| Migrations  | New versions, never edits. | You can run V2 against bad data and fix it safely.          |
| Constraints | PK, FK, UNIQUE, CHECK.     | EXCLUDE, and why order inside a migration matters.          |
| Design      | Plans in their own table.  | Why the paid price stays on the membership.                 |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any schema change:

- Is it a new migration, with every released one untouched?
- Does each rule in the Java code have a named constraint, and a test that bypasses Java?
- What happens to existing rows that break the new rule?
- Are values stored in one form, so `UNIQUE` means what it should?
