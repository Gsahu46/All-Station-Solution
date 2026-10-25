# Station 110 · Account deletion and data export

Working Systems · 0–2 years · Core · Social · Types: Database, Security

Spring Boot 4.1.1 · Java 25 · JdbcClient · @Scheduled jobs · Spring Security with database users · PostgreSQL 17 (jsonb, information_schema) · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Members, posts, invoices and phone numbers are demo data; nothing is sent to anyone. The legal points are summarised for learning, not legal advice: the retention periods and the 90-day deadline here are demo rules.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 12 tests.

# 1 · Understand

## The problem in real life

1.  **Delete my account**

    A Chaupal member asked for a copy of their data and then for their account to be deleted, as India's data protection law lets them.

2.  **Still in nine tables**

    The deletion code followed the member's user id. Weeks later their phone number was still in the table of sign-in codes, in another member's address-book upload, in a queue of unsent notifications and in old support tickets: tables that know the number, not the id.

3.  **The fix**

    An inventory of every table, checked against the database on every build. Deleting runs the whole inventory in one transaction; what the law requires is kept, and says why; and a test searches every text column of every table for the number afterwards.

You can only delete what you know you have. Keep the list of where personal data lives, and make the build fail when it is incomplete.

## What are we building?

A data export and an account deletion that reach every copy of a person's data, keep only what the law requires, and prove it.

## An everyday analogy

Moving out of a flat: you do not just take your name off the door. You collect your post, cancel deliveries, take your number off the building's contact list, and leave only the rent receipts the landlord must keep.

## How it works in 4 steps

1.  **Inventory**: every table is listed with how it points at a person and what happens to it.
2.  **Close**: `DELETE /me` closes the account at once and books the erasure.
3.  **Erase**: a job runs the inventory in one transaction: delete, anonymise, or keep with a reason.
4.  **Prove**: a test searches every text column for the person afterwards; another fails when a table is missing from the inventory.

Check yourself: why not delete the user row and let ON DELETE CASCADE do the rest?

Cascades follow foreign keys. The sign-in codes, others' address books and the notification queue hold the phone number with no key to the user row, so nothing cascades to them. And the invoices, which do have a key, must not be deleted at all.

## What this station is not

- **Not legal advice.** The law is summarised with its status; the numbers are demo rules.
- **No backups or log files.** They are discussed in Production and challenge 3, not simulated.
- **No consent screens.** Consent notices are another part of the DPDP Rules.

## Key terms

| Term                              | Simple meaning                                                                                     | Everyday example                                          | In this project                        |
|-----------------------------------|----------------------------------------------------------------------------------------------------|-----------------------------------------------------------|----------------------------------------|
| **Personal data**                 | Anything that identifies a person: name, phone, email, what they wrote, where they signed in from. | Your name on a parcel.                                    | phone, posts, sign-ins                 |
| **Data inventory**                | A list of every place personal data is kept and what happens to it.                                | A list of every cupboard in the house, and what is in it. | `PersonalData`                         |
| **Delete or anonymise**           | Remove the row, or keep the row with nothing that identifies the person in it.                     | Shredding a form, or blacking out the name on it.         | posts deleted; the user row anonymised |
| **Keeping what the law requires** | Some records must stay for a set time, deletion request or not.                                    | A shop keeps its sales receipts for the tax office.       | invoices, sign-in records              |
| **Export as a job**               | Collecting someone's data takes a while; it is prepared in the background and fetched later.       | Ordering a photo print and picking it up.                 | `POST /me/data-export`                 |
| **DPDP Act**                      | India's Digital Personal Data Protection Act, 2023, and its Rules of 2025.                         | The rulebook for how a business treats your data.         | the station's reason                   |

# 2 · Build: Spec

## Business problem

**Chaupal** (a fictional community app): a member's phone number survived their deletion request in nine tables.

## Acceptance criteria

Demo rules: erasure due within 90 days of the request (done by the next job run, every 5 s here); sign-in records kept 180 days; invoices kept until their retention date.

1.  **Given** a member, **then** `POST /me/data-export` answers `202`; the export becomes READY and holds their own data, not others' address books that mention them.
2.  **Given** `DELETE /me`, **then** `202`; from that moment the account cannot sign in.
3.  **Given** the erasure has run, **then** the person's phone, email and name appear only in invoices, and nowhere else in any table.
4.  **Given** another member's export id, or an unknown one, **then** `404`; not ready, `409`; a support account, `403`; no sign-in, `401`.
5.  **Given** a new table, **then** the build fails until the inventory says what to do with it.

## Requirements

- The erasure is all or nothing.
- A deleted account's row holds nothing that identifies the person: a named CHECK.
- Logs never hold the data being erased.

## Learning objectives

- Build a personal data inventory and keep it true with a test.
- Choose delete, anonymise or keep, per table, with a reason.
- Run exports and erasures as background jobs.
- Prove an erasure by searching the data, not by trusting the code.

# 2 · Build: API contract

## Endpoints

| Method   | Path                         | Purpose                                                          |
|----------|------------------------------|------------------------------------------------------------------|
| `POST`   | `/me/data-export`            | Ask for a copy of your data: `202` and its address.              |
| `GET`    | `/me/data-exports/{id}`      | PENDING or READY.                                                |
| `GET`    | `/me/data-exports/{id}/file` | The JSON, as an attachment.                                      |
| `DELETE` | `/me`                        | Close the account and book the erasure: `202` with its due date. |

## Status codes

| Status    | When                                    |
|-----------|-----------------------------------------|
| 202 / 200 | Accepted as a job / read                |
| 400       | An id that is not a number              |
| 401       | Not signed in, or the account is closed |
| 403       | A support account: it has no "me"       |
| 404       | No such export of yours                 |
| 409       | The export is not ready yet             |

## Captured examples

Captured with curl from the running app on 25 Oct 2026, in this order. `Date`, connection and standard security headers are left out.

``` code
Rows holding 9811122233, by table and column, before:
contact_uploads.contact_phone: 1
invoices.buyer_phone: 1
notification_outbox.phone: 1
otp_requests.phone: 1
posts.body: 1
support_tickets.phone: 1
users.phone: 1
```

### Case 1: Imran asks for his data

**Why:** `202`: a job.

Request

``` code
POST /me/data-export HTTP/1.1
Authorization: Basic aW1yYW46aW1yYW4tZGVtby1wYXNz
```

Response

``` code
HTTP/1.1 202 
Location: /me/data-exports/1
Content-Type: application/json

{
  "id": 1,
  "status": "PENDING",
  "requestedAt": "2026-10-25T04:08:28.229919Z",
  "readyAt": null
}
```

### Case 2: a moment later

**Why:** READY.

Request

``` code
GET /me/data-exports/1 HTTP/1.1
Authorization: Basic aW1yYW46aW1yYW4tZGVtby1wYXNz
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 109

{
  "id": 1,
  "status": "READY",
  "requestedAt": "2026-10-25T04:08:28.229919Z",
  "readyAt": "2026-10-25T04:08:32.616521Z"
}
```

### Case 3: the file

**Why:** his account, profile, posts, comments, invoices, sign-ins, tickets and his own address book; not Zoya's upload that mentions him.

Request

``` code
GET /me/data-exports/1/file HTTP/1.1
Authorization: Basic aW1yYW46aW1yYW4tZGVtby1wYXNz
```

Response

``` code
HTTP/1.1 200 
Content-Disposition: attachment; filename="chaupal-data-1.json"
Content-Type: application/json
Content-Length: 930

{
  "posts": [
    {
      "id": 1,
      "body": "Anyone up for cricket at Gomti Nagar on Sunday? Call me on +919811122233.",
      "created_at": "2026-10-25T04:08:26.617Z"
    }
  ],
  "account": [
    {
      "name": "Imran Qureshi",
      "email": "imran.q@example.com",
      "phone": "+919811122233"
    }
  ],
  "profile": [
    {
      "bio": "Weekend cricket and old Hindi songs",
      "city": "Lucknow",
      "date_of_birth": "1990-02-14T00:00:00.000Z"
    }
  ],
  "signIns": [
    {
      "at": "2026-04-08T04:08:26.617Z",
      "ip": "203.0.113.10"
    },
    {
      "at": "2026-10-23T04:08:26.617Z",
      "ip": "203.0.113.11"
    }
  ],
  "comments": [
    {
      "id": 2,
      "body": "I will bring snacks.",
      "post_id": 2,
      "created_at": "2026-10-25T04:08:26.617Z"
    }
  ],
  "invoices": [
    {
      "id": 1,
      "issued_on": "2026-04-01T00:00:00.000Z",
      "buyer_name": "Imran Qureshi",
      "buyer_phone": "+919811122233",
      "amount_paise": 49900
    }
  ],
  "supportTickets": [
    {
      "id": 1,
      "message": "I cannot change my profile photo."
    }
  ],
  "contactsYouUploaded": [
    {
      "contact_name": "Zoya",
      "contact_phone": "+919822233344"
    }
  ]
}
```

### Case 4: Zoya asks for export 1

**Why:** `404`: it is not hers.

Request

``` code
GET /me/data-exports/1 HTTP/1.1
Authorization: Basic em95YTp6b3lhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "instance": "/me/data-exports/1",
  "status": 404,
  "title": "Not Found"
}
```

### Case 5: a support account calls `DELETE /me`

**Why:** `403`.

Request

``` code
DELETE /me HTTP/1.1
Authorization: Basic c3VwcG9ydDpzdXBwb3J0LWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 403 
Content-Type: application/problem+json
Content-Length: 93

{
  "title": "Not allowed",
  "status": 403,
  "detail": "This sign-in cannot do this.",
  "instance": "/me"
}
```

### Case 6: Imran deletes his account

**Why:** `202`; due within 90 days.

Request

``` code
DELETE /me HTTP/1.1
Authorization: Basic aW1yYW46aW1yYW4tZGVtby1wYXNz
```

Response

``` code
HTTP/1.1 202 
Content-Type: application/json

{
  "status": "DELETION_REQUESTED",
  "dueBy": "2027-01-23T04:08:33.176577Z"
}
```

### Case 7: Imran signs in again

**Why:** `401`: closed at once.

Request

``` code
GET /me/data-exports/1 HTTP/1.1
Authorization: Basic aW1yYW46aW1yYW4tZGVtby1wYXNz
```

Response

``` code
HTTP/1.1 401 
Content-Type: application/problem+json
Content-Length: 120

{
  "title": "Sign-in required",
  "status": 401,
  "detail": "Send a valid username and password.",
  "instance": "/me/data-exports/1"
}
```

## After the erasure

The same search of every text column, then his row and the ledger:

``` code
Rows holding 9811122233, by table and column, after:
invoices.buyer_phone: 1
```

``` code
id | login | name | phone | email | status  
----+-------+------+-------+-------+---------
  1 |       |      |       |       | DELETED
(1 row)

 user_id | requested_at |   due_by   | done 
---------+--------------+------------+------
       1 | 2026-10-25   | 2027-01-23 | t
(1 row)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                               | What happens                                                                             | Proved by                                                      |
|------------------------------------|------------------------------------------------------------------------------------------|----------------------------------------------------------------|
| The old delete by user id          | The number left in 3 tables besides invoices                                             | `theOldWayLeavesHisNumberInTablesThatDoNotKnowHisUserId`       |
| The API's erasure                  | Phone and name only in invoices; email, posts gone; Zoya's post kept; the account closed | `theApiErasesHimEverywhereExceptWhatTheLawKeeps`               |
| An export                          | A job; the person's own data, not others' that mention them                              | `anExportIsAJobAndHoldsThePersonsOwnDataOnly`                  |
| Deleting                           | Closed at once; due within 90 days; recent sign-ins kept, old ones gone                  | `deletingClosesTheAccountAtOnceAndBooksTheErasureWithin90Days` |
| Unknown export; bad id             | `404`; `400`                                                                             | `anUnknownExportIs404AndABadIdIs400`                           |
| No sign-in; a support account      | `401`; `403`                                                                             | `noSignInIs401AndASupportAccountHasNoMe`                       |
| Another member's export            | `404`                                                                                    | `onePersonCannotReadAnothersExport`                            |
| Not ready                          | `409`                                                                                    | `anExportNotYetReadyIs409`                                     |
| A table missing from the inventory | The build fails                                                                          | `everyTableHasAnEntryInTheInventoryAndEveryEntryATable`        |
| An entry with no reason or no SQL  | The build fails                                                                          | `everyEntryThatKeepsOrDeletesSaysWhy`                          |
| Plain SQL against the rules        | Named constraints                                                                        | `theRulesAreNamedConstraintsInTheDatabase`                     |
| An erasure that fails half-way     | Nothing erased                                                                           | `anErasureThatFailsHalfWayErasesNothing`                       |

## The trap

Plausible but wrong

Deleting from one table while copies remain in logs, backups and other tables.

- **The old way.** Delete every row that hangs off the user id, blank the user row. Every table that knows the id is clean. The test then searches every text column of every table for his number: it is still in other members' address-book uploads, the unsent notification queue and the sign-in codes, besides the invoices the law keeps.
- **The API.** The same search after `DELETE /me` finds the number in the invoices only.

While building, each part was undone once: the sign-in codes left out turned 1 test red; others' address books left out 1; the user row not anonymised 2; no transaction around the erasure 1; deleted accounts still able to sign in 1; others' address books in the export 1; another member's export readable 1; recent sign-in records deleted 1; a table missing from the inventory 1.

``` code
package com.chaupal.accounts;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Imran asks Chaupal to delete his account. Where is his phone number afterwards? Written first. */
class AccountDeletionTrapTest extends ApiTest {

    /** The old way: delete what hangs off his user id, blank his row. Every table found through the user id is clean. */
    void oldDelete(long user) {
        for (String table : new String[]{"profiles", "comments", "posts", "login_events", "support_tickets", "data_exports"}) {
            jdbc.sql("DELETE FROM " + table + " WHERE user_id = ?").param(user).update();
        }
        jdbc.sql("UPDATE users SET login = NULL, password_hash = NULL, name = NULL, phone = NULL, email = NULL, status = 'DELETED', deleted_at = now() WHERE id = ?")
                .param(user).update();
    }

    @Test
    void theOldWayLeavesHisNumberInTablesThatDoNotKnowHisUserId() {
        assertThat(foundIn(IMRANS_DIGITS)).hasSizeGreaterThan(5);   // before: everywhere
        oldDelete(1);
        assertThat(foundIn(IMRANS_DIGITS)).containsExactlyInAnyOrder(
                "contact_uploads.contact_phone",   // in Zoya's address book upload
                "invoices.buyer_phone",            // kept by law: fine
                "notification_outbox.phone",       // a message still waiting to be sent to him
                "otp_requests.phone");             // his sign-in codes
    }

    @Test
    void theApiErasesHimEverywhereExceptWhatTheLawKeeps() throws Exception {
        deleteMe("imran").andExpect(status().isAccepted());
        eraseNow(1);
        assertThat(foundIn(IMRANS_DIGITS)).containsExactly("invoices.buyer_phone");
        assertThat(foundIn("Imran Qureshi")).containsExactly("invoices.buyer_name");
        assertThat(foundIn("imran.q@example.com")).isEmpty();
        assertThat(foundIn("Gomti Nagar")).as("his post").isEmpty();
        assertThat(foundIn("Book club")).as("Zoya's post is hers").isNotEmpty();
        as("imran", get("/me/data-exports/1")).andExpect(status().isUnauthorized());   // the account is closed
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
docker compose up -d --wait   # PostgreSQL 17 on localhost:5432
./mvnw spring-boot:run        # the API on http://localhost:8080
./mvnw test                   # all 12 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d --wait
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Add a table that holds a phone number, without touching `PersonalData`, and run the tests:

``` code
printf 'CREATE TABLE referral_invites (id BIGSERIAL PRIMARY KEY, phone TEXT NOT NULL);\n' > src/main/resources/db/migration/V3__invites.sql
./mvnw test -Dtest=PersonalDataInventoryTest   # fails: referral_invites has no entry
```

Then decide what happens to it, add the entry, and run the trap test too.

## Troubleshooting

| You see                                             | Cause                                                                                   | Fix                                                     |
|-----------------------------------------------------|-----------------------------------------------------------------------------------------|---------------------------------------------------------|
| `PersonalDataInventoryTest` fails after a migration | A new table with no decision.                                                           | Add an entry: action, reason, SQL.                      |
| An erasure keeps failing in the log                 | Something blocks a delete (a new foreign key, for instance); it rolls back and retries. | Add the new table to the inventory, in the right order. |
| `401` right after `DELETE /me`                      | Expected: the account is closed.                                                        |                                                         |

## Project layout

``` tree
stations/110-account-deletion-and-data-export/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/chaupal/accounts/
│   ├── PersonalData.java   ├── Accounts.java   ├── MeController.java   ├── SecurityConfig.java
│   └── ProblemResponses.java, AccountsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__chaupal.sql, V2__demo_data.sql
├── src/test/java/com/chaupal/accounts/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

The inventory first, then in the order a request travels.

#### `src/main/java/com/chaupal/accounts/PersonalData.java`

Does  
The inventory.

Why  
Every table: what links it to a person, the action, the reason, the SQL. The erasure runs it in order.

Without it  
A table nobody remembered.

- Tables found by phone, not user id, are the ones the old code missed: `otp_requests`, `notification_outbox`, and `contact_uploads.contact_phone` in other members' rows.

#### `src/main/java/com/chaupal/accounts/Accounts.java`

Does  
Exports and erasures.

Why  
Exports built from a list of the person's own data; the erasure runs the inventory in one transaction; a nightly purge of old sign-ins.

Without it  
Half an erasure; one failing account holding up the others.

- The job calls `erase` through the Spring proxy (`self`), so each account gets its own transaction; called directly, `@Transactional` would be skipped.

#### `src/main/java/com/chaupal/accounts/MeController.java`

The four endpoints; "me" is always the signed-in account.

#### `src/main/java/com/chaupal/accounts/SecurityConfig.java`

Does  
Sign-in.

Why  
Accounts from the database, ACTIVE only: a deletion request closes the account at once.

Without it  
Signing in to an account being erased.

#### `src/main/resources/db/migration/V1__chaupal.sql`

Does  
Tables.

Why  
Named CHECKs: a deleted user holds nothing; erasures due within 90 days; invoices kept past their date of issue.

Without it  
A "deleted" account with its phone number still in it.

#### `src/main/resources/db/migration/V2__demo_data.sql`

Imran, Zoya and a support account; Imran's number is in seven columns of seven tables (the scan before, on the API contract tab).

#### `src/main/resources/application.yaml`

Job timings.

#### `compose.yaml`

PostgreSQL 17 for running the app.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                                                  | Result |
|---------------|-------------------------------------------------------|-------------------------------------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found              | `AccountContractTest` (3)                                   | pass   |
| Every station | Reproduce the failure before the fix                  | `AccountDeletionTrapTest` (2)                               | pass   |
| Database      | Rollback and constraint tests against a real database | `AccountDatabaseTest` (2), `PersonalDataInventoryTest` (2)  | pass   |
| Security      | 401, 403, another user's data, malicious input        | `AccountSecurityTest` (3), and the 400 in the contract test | pass   |

The trap test does not trust the deletion code: it lists every text column of every table from `information_schema` and searches each one for the person's number, name and email. The jobs run when a test calls them, not on their timer: the first version let the 100 ms job run beside each test's reset of the data, and a mutation run ended in a database deadlock between the two.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.chaupal.accounts.PersonalDataInventoryTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.chaupal.accounts.AccountContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.chaupal.accounts.AccountSecurityTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.chaupal.accounts.AccountDatabaseTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.chaupal.accounts.AccountDeletionTrapTest
[INFO] Tests run: 12, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/chaupal/accounts/AccountDeletionTrapTest.java`

Written first: the old delete and the API, searched column by column.

#### `src/test/java/com/chaupal/accounts/PersonalDataInventoryTest.java`

The inventory against the database.

#### `src/test/java/com/chaupal/accounts/AccountContractTest.java`

Exports, deletion, bad ids.

#### `src/test/java/com/chaupal/accounts/AccountSecurityTest.java`

Sign-in, roles, another member's export.

#### `src/test/java/com/chaupal/accounts/AccountDatabaseTest.java`

Named constraints; an erasure that fails half-way.

#### `src/test/java/com/chaupal/accounts/ApiTest.java`

Shared setup and the search of every column.

#### `src/test/java/com/chaupal/accounts/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/chaupal/accounts/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=ExportExpiryChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 12 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 15 tests pass (12 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Exports expire

An export is a full copy of a person's data. Seven days after it is ready, the file answers `410 Gone`, and the job empties its content.

**Done when:** the test in `ExportExpiryChallengeTest` passes.

Hints

- Compare `ready_at` with now in the query that reads the file.
- An emptied export is no longer READY with content: mind the `data_exports_ready_has_content` CHECK (a new status, EXPIRED).

#### `challenge/ExportExpiryChallengeTest.java`

``` code
package com.chaupal.accounts;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: an export is a copy of everything about a person; it should not sit there for ever. 7 days, then 410. */
class ExportExpiryChallengeTest extends ApiTest {

    @Test
    void aReadyExportCanBeDownloadedForSevenDaysThenItIsGone() throws Exception {
        requestExport("zoya").andExpect(status().isAccepted());
        accounts.runJobs();
        exportFile("zoya", 1).andExpect(status().isOk());

        jdbc.sql("UPDATE data_exports SET ready_at = now() - interval '8 days' WHERE id = 1").update();
        exportFile("zoya", 1).andExpect(status().isGone());
        accounts.runJobs();
        assertThat(jdbc.sql("SELECT content IS NULL FROM data_exports WHERE id = 1").query(Boolean.class).single()).isTrue();
        assertThat(foundIn("meets Friday")).as("the copy inside the export is gone too").containsExactly("posts.body");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 40 minutes

## Accounts nobody uses

`Accounts.sweepInactive()`: a member with no sign-in for three years gets one notice ("... erased in 48 hours unless you sign in"); 48 hours after it, still with no sign-in, their erasure is booked. A sign-in after the notice keeps the account.

**Done when:** both tests in `InactiveAccountChallengeTest` pass.

Hints

- Record when the notice went out (a column, in a new migration), so one sweep never sends two.
- "No sign-in since" is the newest `login_events.at`.
- Reuse `requestDeletion`.

#### `challenge/InactiveAccountChallengeTest.java`

``` code
package com.chaupal.accounts;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 2: accounts nobody has used for three years are erased, after a notice 48 hours before. Accounts.sweepInactive()
 * sends the notice once, and books the erasure when the 48 hours have passed with no sign-in.
 */
class InactiveAccountChallengeTest extends ApiTest {

    String status(long user) {
        return jdbc.sql("SELECT status FROM users WHERE id = ?").param(user).query(String.class).single();
    }

    int notices(String phone) {
        return jdbc.sql("SELECT count(*) FROM notification_outbox WHERE phone = ? AND text LIKE '%48 hours%'").param(phone).query(Integer.class).single();
    }

    @Test
    void threeQuietYearsANoticeThen48HoursThenErasure() {
        jdbc.sql("INSERT INTO login_events (user_id, ip, at) VALUES (2, '198.51.100.7', now() - interval '3 years 1 day')").update();
        accounts.sweepInactive();
        accounts.sweepInactive();
        assertThat(notices("+919822233344")).as("one notice, not one per sweep").isEqualTo(1);
        assertThat(status(2)).isEqualTo("ACTIVE");

        jdbc.sql("UPDATE users SET inactivity_notice_at = now() - interval '49 hours' WHERE id = 2").update();
        accounts.sweepInactive();
        assertThat(status(2)).isIn("DELETION_REQUESTED", "DELETED");
    }

    @Test
    void signingInAfterTheNoticeKeepsTheAccount() {
        jdbc.sql("INSERT INTO login_events (user_id, ip, at) VALUES (2, '198.51.100.7', now() - interval '3 years 1 day')").update();
        accounts.sweepInactive();
        jdbc.sql("UPDATE users SET inactivity_notice_at = now() - interval '49 hours' WHERE id = 2").update();
        jdbc.sql("INSERT INTO login_events (user_id, ip, at) VALUES (2, '198.51.100.7', now() - interval '1 hour')").update();
        accounts.sweepInactive();
        assertThat(status(2)).isEqualTo("ACTIVE");
        assertThat(status(1)).as("Imran signed in 2 days ago").isEqualTo("ACTIVE");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## The backup from last week

The database is restored from a backup taken eight days ago. Five accounts erased since then are back, with their data. Design what happens next using the `erasures` ledger (it holds no personal data, so it can live outside the backup), how long backups are kept, and what you tell a member who asks whether their data is "really" gone.

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: delete the old way, then search every column.
2.  Write the inventory, every table, with a test that compares it with the database.
3.  Run it as one transaction; anonymise the user row; keep what the law requires.
4.  Exports as jobs, from a list of the person's own data.

## Design alternatives and trade-offs

| Approach                                              | What it costs                                                                       | Verdict                            |
|-------------------------------------------------------|-------------------------------------------------------------------------------------|------------------------------------|
| An explicit inventory checked against the schema      | A list to keep up; the test makes it impossible to forget.                          | Chosen                             |
| Follow foreign keys to users                          | No list; misses everything keyed by phone or email, and deletes what the law keeps. | See Review                         |
| Delete the user row with ON DELETE CASCADE            | Same blind spots, and no way to keep invoices.                                      | Avoid                              |
| Anonymise everything, delete nothing                  | Content can still identify (a post with a phone number in it).                      | Only where content is not personal |
| Crypto-shredding (encrypt per person, delete the key) | Reaches backups too; every read decrypts.                                           | For large systems                  |

## Database design

| Object                           | Rule                                                       | Why                                        |
|----------------------------------|------------------------------------------------------------|--------------------------------------------|
| `users_deleted_holds_nothing`    | DELETED means login, password, name, phone, email are NULL | "Deleted" cannot be a label on a full row. |
| `erasures_within_90_days`        | due_by ≤ requested_at + 90 days                            | The deadline is part of the record.        |
| `invoices_retained_after_issue`  | retain_until \> issued_on                                  | A kept record says until when.             |
| `data_exports_ready_has_content` | READY means content                                        | No empty "ready" exports.                  |

**Transaction boundaries:** the deletion request (close the account, book the erasure) is one transaction; each account's erasure is another, all or nothing; an export is built in its own.

# 3 · Go deeper: Production

## Real-world considerations

The law, with its status  
India's Digital Personal Data Protection Act, 2023 gives people the right to have their data erased. The DPDP Rules, 2025 were notified in November 2025 and apply in phases; the duties on keeping and erasing data are due to apply from May 2027. They include erasing data once its purpose is served or consent is withdrawn, unless a law requires keeping it, and, for some large platforms, erasing after three years of inactivity with notice 48 hours before. This station's 90-day deadline is a demo rule, not a figure taken from the law. Not legal advice: read the current text with counsel.

Keeping what the law requires  
Tax invoices: India's GST law asks for accounts and records to be kept for years (72 months from the due date of the annual return under the CGST Act). Security logs: CERT-In's directions of April 2022 ask for system logs to be kept for 180 days. Keep these, restrict who can read them, and delete them when the period ends.

Logs  
Do not write personal data into application logs at all: then there is nothing to erase there. This station logs account ids only.

Backups  
You cannot edit a backup. Keep backups for a short, stated period, and re-apply the erasure ledger after any restore (challenge 3).

Other systems  
Search indexes, analytics, the email provider, the data warehouse: each needs its own entry in the inventory and its own erasure step.

Watching it  
Alert on any erasure not completed one day after its request, long before its due date.

# 3 · Go deeper: Interview

## Interview takeaways

How do you make sure a deletion reaches every copy?

An inventory of every place personal data is kept, checked against the schema in a test, and a test that searches the data afterwards.

Delete or anonymise?

Delete what has no reason to stay; anonymise rows others depend on (keep the id, remove what identifies); keep what a law requires, with an end date.

Why is an export a background job?

Collecting everything can be slow and large; a job can be retried, and the result fetched when ready.

What about backups?

Short retention, and a ledger of erasures re-applied after any restore; or crypto-shredding.

What must not be in an export?

Other people's data, even when it mentions the person: someone else's address book is theirs.

How do you stop a deleted account being used during the erasure?

Close it in the same request: sign-in only for ACTIVE accounts.

## Self-check rubric

| Area        | Meets the bar                      | Above the bar                                                                  |
|-------------|------------------------------------|--------------------------------------------------------------------------------|
| Correctness | All 12 tests pass.                 | You ran the flawed version and explained each failure.                         |
| Inventory   | Tables listed.                     | The build fails when one is missing, and each entry says why.                  |
| Erasure     | Rows deleted.                      | All or nothing, proven by searching every column, with the kept records named. |
| The law     | Knows there is a right to erasure. | Can say what the Rules require, when they apply, and what to keep.             |

# 3 · Go deeper: Review

## The pull request

A teammate replaces the hand-written inventory: "read the foreign keys to `users` from the database, and no table is ever forgotten". Read the file and list every problem before opening the findings.

#### `review/Accounts.java`

``` code
package com.chaupal.accounts;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Lazy;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.json.JsonMapper;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/** Data exports and account deletion, both as background jobs. */
@Service
class Accounts {

    record Export(long id, String status, Instant requestedAt, Instant readyAt) {
    }

    record Deletion(String status, Instant dueBy) {
    }

    private static final Logger log = LoggerFactory.getLogger(Accounts.class);
    // What a person gets in their export: their own data. Others' address books that hold their number are not theirs.
    private static final Map<String, String> EXPORTED = new LinkedHashMap<>();

    static {
        EXPORTED.put("account", "SELECT name, phone, email FROM users WHERE id = :user");
        EXPORTED.put("profile", "SELECT bio, city, date_of_birth FROM profiles WHERE user_id = :user");
        EXPORTED.put("posts", "SELECT id, body, created_at FROM posts WHERE user_id = :user ORDER BY id");
        EXPORTED.put("comments", "SELECT id, post_id, body, created_at FROM comments WHERE user_id = :user ORDER BY id");
        EXPORTED.put("contactsYouUploaded", "SELECT contact_name, contact_phone FROM contact_uploads WHERE uploader_id = :user ORDER BY id");
        EXPORTED.put("invoices", "SELECT id, buyer_name, buyer_phone, amount_paise, issued_on FROM invoices WHERE user_id = :user ORDER BY id");
        EXPORTED.put("signIns", "SELECT ip, at FROM login_events WHERE user_id = :user ORDER BY at");
        EXPORTED.put("supportTickets", "SELECT id, message FROM support_tickets WHERE user_id = :user ORDER BY id");
    }

    private final JdbcClient jdbc;
    private final JsonMapper json;
    private final Accounts self;   // through the proxy, so erase() runs in its own transaction

    Accounts(JdbcClient jdbc, JsonMapper json, @Lazy Accounts self) {
        this.jdbc = jdbc;
        this.json = json;
        this.self = self;
    }

    long idOf(String login) {
        return jdbc.sql("SELECT id FROM users WHERE login = ?").param(login).query(Long.class).single();
    }

    Export requestExport(long user) {
        long id = jdbc.sql("INSERT INTO data_exports (user_id) VALUES (?) RETURNING id").param(user).query(Long.class).single();
        return export(user, id).orElseThrow();
    }

    /** Another person's export is not found, the same as one that does not exist. */
    Optional<Export> export(long user, long id) {
        return jdbc.sql("SELECT id, status, requested_at, ready_at FROM data_exports WHERE id = ? AND user_id = ?").params(id, user)
                .query(Export.class).optional();
    }

    Optional<String> exportFile(long user, long id) {
        return jdbc.sql("SELECT content::text FROM data_exports WHERE id = ? AND user_id = ? AND status = 'READY'").params(id, user)
                .query(String.class).optional();
    }

    /** Signs the person out for good (status is no longer ACTIVE) and books the erasure, due within 90 days. */
    @Transactional
    Deletion requestDeletion(long user) {
        jdbc.sql("UPDATE users SET status = 'DELETION_REQUESTED', deletion_requested_at = now() WHERE id = ? AND status = 'ACTIVE'").param(user).update();
        jdbc.sql("INSERT INTO erasures (user_id, requested_at, due_by) VALUES (?, now(), now() + interval '90 days') ON CONFLICT DO NOTHING").param(user).update();
        return jdbc.sql("SELECT u.status, e.due_by FROM users u JOIN erasures e ON e.user_id = u.id WHERE u.id = ?").param(user).query(Deletion.class).single();
    }

    @Scheduled(fixedDelayString = "${chaupal.jobs.every}")
    void runJobs() {
        jdbc.sql("SELECT id, user_id FROM data_exports WHERE status = 'PENDING' ORDER BY id")
                .query((rs, n) -> new long[]{rs.getLong(1), rs.getLong(2)}).list().forEach(e -> buildExport(e[0], e[1]));
        for (long user : jdbc.sql("SELECT id FROM users WHERE status = 'DELETION_REQUESTED' ORDER BY id").query(Long.class).list()) {
            try {
                self.erase(user);
            } catch (RuntimeException e) {
                // One account that cannot be erased must not hold up the others; it is tried again next time.
                log.error("Erasure of account {} failed and was rolled back: {}", user, e.getMessage());
            }
        }
    }

    void buildExport(long id, long user) {
        Map<String, Object> content = new LinkedHashMap<>();
        EXPORTED.forEach((name, sql) -> content.put(name, jdbc.sql(sql).param("user", user).query().listOfRows()));
        jdbc.sql("UPDATE data_exports SET status = 'READY', content = ?::jsonb, ready_at = now() WHERE id = ? AND status = 'PENDING'")
                .params(json.writeValueAsString(content), id).update();
    }

    /**
     * Everything personal points at users, so the foreign keys say where it is: read them from the database, delete
     * the person's rows in each table, then blank the account. No hand-kept list to forget a table in.
     */
    @Transactional
    void erase(long user) {
        List<String[]> references = jdbc.sql("""
                        SELECT kcu.table_name, kcu.column_name
                        FROM information_schema.referential_constraints rc
                        JOIN information_schema.key_column_usage kcu ON kcu.constraint_name = rc.constraint_name
                        JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = rc.unique_constraint_name
                        WHERE ccu.table_name = 'users' AND kcu.table_name <> 'erasures'
                        ORDER BY kcu.table_name""")
                .query((rs, n) -> new String[]{rs.getString(1), rs.getString(2)}).list();
        for (String[] r : references) {
            jdbc.sql("DELETE FROM " + r[0] + " WHERE " + r[1] + " = ?").param(user).update();
        }
        jdbc.sql("UPDATE users SET login = NULL, password_hash = NULL, name = NULL, phone = NULL, email = NULL, "
                + "status = 'DELETED', deleted_at = now() WHERE id = ?").param(user).update();
        jdbc.sql("UPDATE erasures SET completed_at = now() WHERE user_id = ?").param(user).update();
        log.info("Account {} erased", user);
    }

    /** Sign-in records older than 180 days, for everyone. */
    @Scheduled(cron = "${chaupal.jobs.purge-cron}")
    void purgeLoginEvents() {
        jdbc.sql("DELETE FROM login_events WHERE at < now() - interval '180 days'").update();
    }
}
```

## Findings

1Following foreign keys misses what is keyed by phone

"Everything personal points at users, so read the foreign keys and nothing is ever forgotten": the sign-in codes, the notification queue and other members' address books hold the phone number with no foreign key. They are never reached.

**Test evidence:** `theApiErasesHimEverywhereExceptWhatTheLawKeeps` fails: the number is still in the codes, the queue and Zoya's upload.

2It deletes what the law keeps

The same loop deletes every row that points at the user: the invoices, which must be kept for years, and the recent sign-in records kept for security.

**Test evidence:** `deletingClosesTheAccountAtOnceAndBooksTheErasureWithin90Days` fails: the sign-in from two days ago is gone; and the invoice the trap test expects to remain has been deleted.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class                  | Fixed version | Flawed version |
|-----------------------------|---------------|----------------|
| `AccountDatabaseTest`       | 2 / 2         | 2 / 2          |
| `AccountSecurityTest`       | 3 / 3         | 3 / 3          |
| `PersonalDataInventoryTest` | 2 / 2         | 2 / 2          |
| `AccountContractTest`       | 3 / 3         | 2 / 3          |
| `AccountDeletionTrapTest`   | 2 / 2         | 1 / 2          |

The flawed version looks more thorough than a hand-written list, and it does clean every table that knows the user id. The search of every column is what shows the difference.
