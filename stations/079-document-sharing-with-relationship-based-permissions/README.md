# Station 079 · Document sharing with relationship-based permissions

Working Systems · 0–2 years · Core · SaaS · Types: Database, Security

Spring Boot 4.1.1 · Java 25 · Zanzibar-style relation tuples · recursive CTEs · Spring Security 7 (HTTP Basic) · JdbcClient · PostgreSQL 17 · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Users, teams, folders and documents are demo data, not Taskloom's. Share notices are rows in a table: no email is sent.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 18 tests.

# 1 · Understand

## The problem in real life

1.  **Thirty checks**

    Taskloom checked sharing with hand-written SQL in 30 places, each slightly different.

2.  **Copied access**

    Sharing a folder with a team wrote a "may read" row for every member onto every document, at that moment. When Asha left the design team, her rows stayed: she opened its documents for a week.

3.  **The fix**

    Every permission is one relationship. Access is worked out from the relationships on every request, so removing Asha from the team removes everything that came from it, at once.

Store why someone has access, not that they have it. Then taking the reason away takes the access.

## What are we building?

Open a document, share it with a person or a team, and list what has been shared with you; all three answer from one table of relationships.

## An everyday analogy

A club does not print a member card for each event. The door checks: are you a member, or the guest of one, today? Leave the club and every door knows at once.

## How it works in 4 steps

1.  **Who are you?** You, plus every team you are in, through teams inside teams.
2.  **What is this?** The document, plus every folder above it.
3.  **Is there a link?** Any owner, editor or viewer tuple from the first set to the second.
4.  **Answer**: the strongest one, or 404 if none.

Check yourself: Neha was never shared anything directly. Why can she open the logo brief?

She is in brand-leads, which is in design; design may view the Brand folder; Logos is inside Brand; the brief is inside Logos. Four tuples, one query: `accessFlowsThroughFoldersAndTeamsInTeams`.

## What this station is not

- **No permission service.** The model is Zanzibar's, but it runs in this app's PostgreSQL. OpenFGA and SpiceDB are compared in Design.
- **No team admin screen.** Tests and captures change teams with one SQL statement.
- **No editing.** Documents are read and shared, not changed.

## Key terms

| Term               | Simple meaning                                                                                    | Everyday example                                             | In this project                     |
|--------------------|---------------------------------------------------------------------------------------------------|--------------------------------------------------------------|-------------------------------------|
| **Relation tuple** | One fact: object, relation, subject. "team design is viewer of folder Brand."                     | One line in a guest list.                                    | `relation_tuples`                   |
| **Userset**        | "Every member of a team" used as one subject.                                                     | "The whole design team" on the guest list.                   | `team:design#member`                |
| **Inheritance**    | Access to a folder is access to what is inside it.                                                | A key to the building opens the hallway too.                 | `parent` tuples                     |
| **ReBAC**          | Relationship-based access control: access worked out from relationships, not stored per document. | "Friends of the host may come in."                           | `Permissions.access`                |
| **Recursive CTE**  | One SQL query that follows links until there are no new ones.                                     | Asking "and who is in that team?" until nobody new turns up. | `WITH RECURSIVE`                    |
| **Zanzibar**       | Google's paper (2019) on one permission system for many products; OpenFGA and SpiceDB follow it.  | One guest list service for every party.                      | the model here, in plain PostgreSQL |

# 2 · Build: Spec

## Business problem

**Taskloom** (a fictional team tool): sharing was checked in 30 places, and a user removed from a team kept its documents for a week.

## Acceptance criteria

Demo workspace: ravi owns four documents; the Brand folder (with Logos inside) is shared with team design (asha, and team brand-leads with neha); meera edits the roadmap; kabir has nothing.

1.  **Given** a document in a folder shared with your team, or a team inside it, **then** you can open it as viewer.
2.  **Given** an editor or owner, **then** they can share with a user or a team (`201`); a viewer gets `403`.
3.  **Given** no relationship at all, **then** `404`, as for a document that does not exist.
4.  **Given** someone leaves a team, **then** the next request no longer finds the team's documents.
5.  **Given** a document added to a shared folder later, **then** the team can open it.
6.  **Given** "shared with me", **then** what you can open and do not own, with your access.

## Requirements

- One table of relationships; every check reads it; nothing is copied.
- The database refuses relations that make no sense for an object type.
- A share and its notice are one transaction.

## Learning objectives

- Model permissions as tuples, with usersets and inheritance.
- Check access with one recursive query, and know why it terminates.
- Explain why copied permissions go stale.
- Compare your own tables with OpenFGA or SpiceDB.

# 2 · Build: API contract

## Endpoints

| Method | Path                 | Purpose                                                                               |
|--------|----------------------|---------------------------------------------------------------------------------------|
| `GET`  | `/docs/{id}`         | The document and `yourAccess`: viewer, editor or owner.                               |
| `POST` | `/docs/{id}/shares`  | `{subject, relation}`: subject `user:name` or `team:name`, relation viewer or editor. |
| `GET`  | `/me/shared-with-me` | Documents you can open and do not own, with your access.                              |

## Status codes

| Status    | When                                                              |
|-----------|-------------------------------------------------------------------|
| 200 / 201 | Read / shared                                                     |
| 400       | A subject or relation of the wrong shape; an unknown user or team |
| 401       | No or wrong credentials                                           |
| 403       | A viewer sharing; a path with no rule                             |
| 404       | No relationship to the document, or no such document              |

## The demo tuples

From `psql` in `docs/capture.sh`, before the requests below. This is the whole permission state.

``` code
      object      | relation |         subject         
------------------+----------+-------------------------
 team:brand-leads | member   | user:neha
 team:design      | member   | user:asha
 team:design      | member   | team:brand-leads#member
 folder:f-brand   | viewer   | team:design#member
 folder:f-logos   | parent   | folder:f-brand
 doc:d-guidelines | owner    | user:ravi
 doc:d-guidelines | parent   | folder:f-brand
 doc:d-logo-brief | owner    | user:ravi
 doc:d-logo-brief | parent   | folder:f-logos
 doc:d-roadmap    | editor   | user:meera
 doc:d-roadmap    | owner    | user:ravi
 doc:d-salaries   | owner    | user:ravi
(12 rows)
```

## Captured examples

Captured with curl from the running app on 21 Oct 2026. JSON bodies are indented for reading; `Date`, connection and standard security headers are left out.

### Case 1: Asha opens a document in the team's folder

**Why:** asha → design → viewer of Brand → the document.

Request

``` code
GET /docs/d-guidelines HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 134

{
  "id": "d-guidelines",
  "title": "Brand guidelines",
  "body": "Use the teal from the palette; never stretch the logo.",
  "yourAccess": "viewer"
}
```

### Case 2: Neha opens the logo brief

**Why:** through a team inside a team and a folder inside a folder.

Request

``` code
GET /docs/d-logo-brief HTTP/1.1
Authorization: Basic bmVoYTpuZWhhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 109

{
  "id": "d-logo-brief",
  "title": "Logo refresh brief",
  "body": "Three directions by Friday.",
  "yourAccess": "viewer"
}
```

### Case 3: shared with Asha

**Why:** both documents from the folder, none of ravi's others.

Request

``` code
GET /me/shared-with-me HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 137

[
  {
    "id": "d-guidelines",
    "title": "Brand guidelines",
    "access": "viewer"
  },
  {
    "id": "d-logo-brief",
    "title": "Logo refresh brief",
    "access": "viewer"
  }
]
```

### Case 4: Kabir asks for the roadmap

**Why:** no relationship: `404`.

Request

``` code
GET /docs/d-roadmap HTTP/1.1
Authorization: Basic a2FiaXI6a2FiaXItZGVtby1wYXNz
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No such document",
  "instance": "/docs/d-roadmap",
  "status": 404,
  "title": "Not Found"
}
```

### Case 5: Meera, an editor, shares it with Kabir

**Why:** `201`: one tuple and one notice.

Request

``` code
POST /docs/d-roadmap/shares HTTP/1.1
Authorization: Basic bWVlcmE6bWVlcmEtZGVtby1wYXNz
Content-Type: application/json

{
  "subject": "user:kabir",
  "relation": "viewer"
}
```

Response

``` code
HTTP/1.1 201 
Content-Type: application/json
Content-Length: 44

{
  "subject": "user:kabir",
  "relation": "viewer"
}
```

### Case 6: Kabir again

**Why:** viewer now.

Request

``` code
GET /docs/d-roadmap HTTP/1.1
Authorization: Basic a2FiaXI6a2FiaXItZGVtby1wYXNz
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 97

{
  "id": "d-roadmap",
  "title": "Q4 roadmap",
  "body": "Ship sharing, then search.",
  "yourAccess": "viewer"
}
```

### Case 7: Asha, a viewer, tries to share

**Why:** `403`: she may know it exists, not pass it on.

Request

``` code
POST /docs/d-guidelines/shares HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "subject": "user:kabir",
  "relation": "viewer"
}
```

Response

``` code
HTTP/1.1 403 
Content-Type: application/problem+json

{
  "detail": "Viewers cannot share",
  "instance": "/docs/d-guidelines/shares",
  "status": 403,
  "title": "Forbidden"
}
```

### Case 8: Asha after leaving the design team

**Why:** one tuple deleted; the next request already says `404`.

Request

``` code
GET /docs/d-guidelines HTTP/1.1
Authorization: Basic YXNoYTphc2hhLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No such document",
  "instance": "/docs/d-guidelines",
  "status": 404,
  "title": "Not Found"
}
```

## The notice written with the share

``` code
  doc_id   | shared_to  | relation | shared_by 
-----------+------------+----------+-----------
 d-roadmap | user:kabir | viewer   | meera
(1 row)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                             | What happens                                     | Proved by                                            |
|--------------------------------------------------|--------------------------------------------------|------------------------------------------------------|
| Owner, editor, viewer                            | The strongest relation wins                      | `accessComesFromTheStrongestRelation`                |
| Folders in folders, teams in teams               | Inherited                                        | `accessFlowsThroughFoldersAndTeamsInTeams`           |
| An editor shares with a user                     | `201`, the user can open it, a notice is written | `anEditorSharesWithAUserAndTheyCanOpenIt`            |
| A share with a team                              | Every member, nested ones too                    | `sharingWithATeamReachesEveryMember`                 |
| Shared with me                                   | What you can open and do not own                 | `sharedWithMeListsWhatICanOpenButDoNotOwn`           |
| Unknown document; bad shares                     | `404`; `400`                                     | `unknownDocumentsAre404AndBadSharesAre400`           |
| No or wrong credentials                          | `401`                                            | `noOrWrongCredentialsAre401`                         |
| A viewer shares; a stranger shares themselves in | `403`; `404`                                     | `aViewerCannotShareAndAStrangerCannotEvenSee`        |
| Another user's or team's access                  | Not yours: `404`                                 | `oneUsersAccessIsNotAnothersAndTeamsDoNotLeakAcross` |
| Paths and methods with no rule                   | `403`                                            | `pathsAndMethodsWithoutARuleAreRefused`              |
| A folder inside itself                           | The check still ends, with the right answers     | `aFolderLoopDoesNotHangTheCheck`                     |
| Odd ids and subjects                             | `400` or `404`, never an error                   | `oddIdsAndSubjectsAre400Or404NeverAnError`           |
| Tuples written by plain SQL                      | Refused by named constraints                     | `tupleRulesHoldWithoutJava`                          |
| A share whose notice fails                       | Nothing granted                                  | `aShareWhoseNoticeFailsGrantsNothing`                |

## The trap

Plausible but wrong

Copying permissions onto each document, so removing someone from a team leaves old access behind.

- **Left the team, kept the documents.** The old copied rows still say Asha may read. With tuples, one row out of the team and her next request is `404`, for both documents and her shared list.
- **Added later, shared never.** A document put into the folder after the share had no copied rows. With tuples the team can open it.
- **Joined later.** A new team member gets the team's documents, and a document shared with the team follows whoever is in it.

While building, each part was undone once: no teams inside teams turned 2 tests red; no folder inheritance 7; viewers allowed to share 1; the share without its transaction 1; owned documents listed as shared 1; no check for unknown users and teams 1; `denyAll` replaced by `authenticated` 1, after a test for paths without a rule was added.

``` code
package com.taskloom.sharing;

import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old sharing code copied permissions: sharing a folder with a team wrote one "may read" row per
 * member onto each document in it, at that moment. Each test runs the old way, then the same change in the tuples.
 */
class CopiedPermissionsTrapTest extends ApiTest {

    /** The old store, as it was: document -> users who may read it, filled in when something was shared. */
    static final class OldAcl {
        final Map<String, Set<String>> readers = new HashMap<>();

        void shareFolderWithTeam(List<String> docsInFolder, List<String> teamMembers) {
            docsInFolder.forEach(d -> readers.computeIfAbsent(d, k -> new HashSet<>()).addAll(teamMembers));
        }

        boolean mayRead(String user, String doc) {
            return readers.getOrDefault(doc, Set.of()).contains(user);
        }
    }

    @Test
    void someoneRemovedFromATeamKeptTheTeamsDocuments() throws Exception {
        OldAcl old = new OldAcl();
        old.shareFolderWithTeam(List.of("d-guidelines", "d-logo-brief"), List.of("asha", "neha"));
        // asha leaves the design team. The team changed; the copied rows did not.
        assertThat(old.mayRead("asha", "d-guidelines")).isTrue();

        open("asha", "d-guidelines").andExpect(status().isOk());
        removeFromTeam("asha", "design");
        open("asha", "d-guidelines").andExpect(status().isNotFound());   // the next request already knows
        open("asha", "d-logo-brief").andExpect(status().isNotFound());
        sharedWithMe("asha").andExpect(jsonPath("$").isEmpty());
    }

    @Test
    void aDocumentAddedLaterWasNotSharedAtAll() throws Exception {
        OldAcl old = new OldAcl();
        old.shareFolderWithTeam(List.of("d-guidelines"), List.of("asha"));
        jdbc.sql("INSERT INTO documents (id, title, body) VALUES ('d-new-icons', 'New icon set', 'Draft.')").update();
        jdbc.sql("INSERT INTO relation_tuples VALUES ('doc', 'd-new-icons', 'parent', 'folder', 'f-brand', ''), ('doc', 'd-new-icons', 'owner', 'user', 'ravi', '')").update();
        assertThat(old.mayRead("asha", "d-new-icons")).isFalse();   // nobody copied rows for it
        open("asha", "d-new-icons").andExpect(status().isOk());      // in the folder, so the team can read it
    }

    @Test
    void aDocumentSharedWithATeamFollowsTheTeamAfterwards() throws Exception {
        share("ravi", "d-roadmap", "team:design", "viewer");
        open("asha", "d-roadmap").andExpect(status().isOk());
        removeFromTeam("asha", "design");
        open("asha", "d-roadmap").andExpect(status().isNotFound());
        jdbc.sql("INSERT INTO relation_tuples VALUES ('team', 'design', 'member', 'user', 'kabir', '')").update();
        open("kabir", "d-roadmap").andExpect(status().isOk());   // joined after the share, sees it anyway
    }

    @Test
    void aNewTeamMemberGetsTheTeamsDocuments() throws Exception {
        jdbc.sql("INSERT INTO relation_tuples VALUES ('team', 'design', 'member', 'user', 'kabir', '')").update();
        open("kabir", "d-guidelines").andExpect(status().isOk());
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
./mvnw test                 # all 18 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Take Neha out of brand-leads and ask again:

``` code
curl -s -o /dev/null -w '%{http_code}\n' -u neha:neha-demo-pass http://localhost:8080/docs/d-guidelines
docker compose exec postgres psql -U taskloom -d taskloom -c "DELETE FROM relation_tuples WHERE object_id = 'brand-leads' AND subject_id = 'neha'"
curl -s -o /dev/null -w '%{http_code}\n' -u neha:neha-demo-pass http://localhost:8080/docs/d-guidelines
```

200, then 404. Nothing else changed: no document row, no cache.

## Troubleshooting

| You see                                           | Cause                                                 | Fix                                                                    |
|---------------------------------------------------|-------------------------------------------------------|------------------------------------------------------------------------|
| `Result value is null but no null value expected` | `single()` on an aggregate over no rows.              | `coalesce` in SQL, or `optional()`. Found while building this station. |
| `relation_tuples_subject` violated                | A team written as a plain subject, without `#member`. | Teams are subjects only as "every member of".                          |

## Project layout

``` tree
stations/079-document-sharing-with-relationship-based-permissions/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/taskloom/sharing/
│   ├── Permissions.java   ├── Documents.java   ├── DocumentController.java
│   ├── SecurityConfig.java   ├── ProblemResponses.java   └── SharingApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__documents_and_relation_tuples.sql, V2__demo_workspace.sql
├── src/test/java/com/taskloom/sharing/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

The permission model first, then the endpoints and the database behind them.

#### `src/main/java/com/taskloom/sharing/Permissions.java`

Does  
The whole permission model: two recursive queries over the tuples.

Why  
Who you are (you and your teams, through teams in teams) and what this is (the document and its folders); the strongest relation between them. The reverse walk lists what is shared with you.

Without it  
Access that outlives the relationship it came from, and thirty slightly different checks.

- `max()` over no rows is `null`, and `JdbcClient`'s `single()` refuses a null value ("Result value is null but no null value expected"): the query uses `coalesce(..., 0)`. Found while building.
- `UNION` (not `UNION ALL`) drops rows already seen, so a folder placed inside itself cannot make the query run forever.

#### `src/main/java/com/taskloom/sharing/Documents.java`

Does  
Open and share.

Why  
No relation is `404`; viewers cannot share; one tuple per share (a team share is one row for the whole team) plus a notice, in one transaction.

Without it  
Team shares copied into member rows, or a viewer handing a document on.

#### `src/main/java/com/taskloom/sharing/DocumentController.java`

Does  
The three endpoints.

Why  
Subjects and relations checked by shape before anything else.

Without it  
Strings like `team:design#member` or SQL in a subject.

#### `src/main/java/com/taskloom/sharing/SecurityConfig.java`

HTTP Basic with demo users; the three paths need a sign-in; everything else refused.

#### `src/main/java/com/taskloom/sharing/ProblemResponses.java`

401 with a Basic challenge and 403 in the same problem JSON as every other error.

#### `src/main/resources/db/migration/V1__documents_and_relation_tuples.sql`

Does  
Documents, tuples, notices.

Why  
Which relations each object type has, what a subject may be, one parent and one owner at most.

Without it  
A tuple that means nothing (a team with an owner, a parent that is a user) written by any tool.

#### `src/main/resources/db/migration/V2__demo_workspace.sql`

The demo workspace: four documents, two folders, two teams, twelve tuples.

#### `src/main/resources/application.yaml`

The database connection.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/taskloom/sharing/SharingApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                       | Test class                      | Result |
|---------------|-------------------------------------------------------------------|---------------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                          | `SharingContractTest` (6)       | pass   |
| Every station | Reproduce the failure before the fix                              | `CopiedPermissionsTrapTest` (4) | pass   |
| Database      | Rollback and constraint tests against a real database             | `SharingDatabaseTest` (2)       | pass   |
| Security      | 401, 403, one user accessing another user's data, malicious input | `SharingSecurityTest` (6)       | pass   |

Before each test the demo workspace is rebuilt from the V2 migration file itself, so every test starts from the tuples shown in the API tab.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.sharing.SharingContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.sharing.SharingDatabaseTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.sharing.CopiedPermissionsTrapTest
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.sharing.SharingSecurityTest
[INFO] Tests run: 18, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/taskloom/sharing/CopiedPermissionsTrapTest.java`

Written first: copied rows that outlive the team, miss new documents; tuples that follow the team.

#### `src/test/java/com/taskloom/sharing/SharingSecurityTest.java`

401, viewers and strangers, access that is not yours, paths with no rule, a folder loop, odd input.

#### `src/test/java/com/taskloom/sharing/SharingDatabaseTest.java`

Every named tuple rule with plain SQL; a share whose notice fails grants nothing.

#### `src/test/java/com/taskloom/sharing/SharingContractTest.java`

Open, share, shared with me, through HTTP.

#### `src/test/java/com/taskloom/sharing/ApiTest.java`

Shared setup: the demo workspace from V2 before each test, request helpers, the team admin's one statement.

#### `src/test/java/com/taskloom/sharing/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/taskloom/sharing/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=UnshareChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 18 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 22 tests pass (18 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## Take a share back

`DELETE /docs/{id}/shares/{subject}` removes that subject's viewer and editor tuples on the document (`204`). Editors and owners only; the owner tuple stays.

**Done when:** both tests in `UnshareChallengeTest` pass.

Hints

- One `DELETE` with `relation IN ('viewer', 'editor')`.
- The same 404 and 403 as sharing.

#### `challenge/UnshareChallengeTest.java`

``` code
package com.taskloom.sharing;

import org.junit.jupiter.api.Test;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: DELETE /docs/{id}/shares/{subject} (subject like user:kabir or team:design) removes that subject's
 * viewer and editor tuples on the document (204). Editors and owners only; the owner tuple is never removed this way.
 */
class UnshareChallengeTest extends ApiTest {

    @Test
    void anOwnerTakesAShareBack() throws Exception {
        share("ravi", "d-roadmap", "user:kabir", "viewer").andExpect(status().isCreated());
        mvc.perform(delete("/docs/d-roadmap/shares/user:kabir").with(httpBasic("ravi", "ravi-demo-pass"))).andExpect(status().isNoContent());
        open("kabir", "d-roadmap").andExpect(status().isNotFound());
    }

    @Test
    void viewersCannotAndTheOwnerStays() throws Exception {
        mvc.perform(delete("/docs/d-guidelines/shares/team:design").with(httpBasic("asha", "asha-demo-pass"))).andExpect(status().isForbidden());
        mvc.perform(delete("/docs/d-roadmap/shares/user:ravi").with(httpBasic("meera", "meera-demo-pass"))).andExpect(status().isNoContent());
        open("ravi", "d-roadmap").andExpect(status().isOk());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 40 minutes

## Who has access?

`GET /docs/{id}/access`: every user who can open the document, with their strongest access, through folders and teams in teams, for editors and owners.

**Done when:** both tests in `WhoHasAccessChallengeTest` pass.

Hints

- Walk up from the document to its folders, collect the subjects of their grants, then walk down from teams to their members.
- Zanzibar calls this expand; it is the check run backwards.

#### `challenge/WhoHasAccessChallengeTest.java`

``` code
package com.taskloom.sharing;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /docs/{id}/access lists every user who can open the document, with their strongest access,
 * through folders and teams in teams (Zanzibar's "expand"), sorted by user. Editors and owners only.
 */
class WhoHasAccessChallengeTest extends ApiTest {

    @Test
    void everyoneWhoCanOpenTheGuidelines() throws Exception {
        mvc.perform(get("/docs/d-guidelines/access").with(httpBasic("ravi", "ravi-demo-pass"))).andExpect(status().isOk())
                .andExpect(jsonPath("$[*].user", contains("asha", "neha", "ravi")))
                .andExpect(jsonPath("$[*].access", contains("viewer", "viewer", "owner")));
    }

    @Test
    void viewersCannotSeeTheList() throws Exception {
        mvc.perform(get("/docs/d-guidelines/access").with(httpBasic("asha", "asha-demo-pass"))).andExpect(status().isForbidden());
        mvc.perform(get("/docs/d-salaries/access").with(httpBasic("kabir", "kabir-demo-pass"))).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Your own tables, or a permission service?

Write the same model in OpenFGA's or SpiceDB's schema language. What would move out of PostgreSQL, what new failure would the app have (the permission service is down), and how do you keep a share and the check that follows it consistent (Zanzibar's zookies, SpiceDB's ZedTokens)? At what size would you switch?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: copied rows that outlive their reason.
2.  One tuple table, with the allowed relations per object type as constraints.
3.  One recursive check: who you are, what this is, the strongest link.
4.  Shares write one tuple, never a copy per member.

## Design alternatives and trade-offs

| Approach                                          | What it costs                                                                   | Verdict                    |
|---------------------------------------------------|---------------------------------------------------------------------------------|----------------------------|
| Tuples in PostgreSQL, recursive CTE per check     | A walk per request; fine for shallow trees.                                     | Chosen                     |
| Copy access rows onto each document               | Stale the moment a team or folder changes.                                      | The trap                   |
| Expand team shares into member rows at write time | Fast reads; misses later members and teams in teams.                            | The review version         |
| OpenFGA or SpiceDB                                | A separate service and its consistency tokens; built-in expand, caching, audit. | At scale, or many products |
| PostgreSQL row-level security on top              | Rules enforced for every query; harder to read.                                 | Defence in depth           |

## Database design

| Object                                     | What                   | Why                                                                              |
|--------------------------------------------|------------------------|----------------------------------------------------------------------------------|
| `relation_tuples_relation_for_type`        | CHECK                  | Teams have members; folders viewers, editors, a parent; documents also an owner. |
| `relation_tuples_subject`                  | CHECK                  | A parent is a folder; any other subject is a user or every member of a team.     |
| `relation_tuples_one_parent`, `_one_owner` | Partial UNIQUE indexes | A tree, not a graph of parents; one owner.                                       |
| `relation_tuples_by_subject`               | Index                  | The walk from a user to their teams.                                             |

**Transaction boundary:** a share (its tuple and its notice) is one transaction. Checks are single statements.

``` code
CREATE TABLE documents (
    id         text CONSTRAINT documents_pk PRIMARY KEY,
    title      text NOT NULL,
    body       text NOT NULL,
    CONSTRAINT documents_id_shape CHECK (id ~ '^[a-z0-9-]{1,40}$'),
    CONSTRAINT documents_title_length CHECK (char_length(title) BETWEEN 1 AND 120)
);

-- Every permission is one tuple: object, relation, subject. "team:design#member is viewer of folder:brand" is one row;
-- who is in team:design is other rows. Access is worked out from the tuples on every request, never copied.
CREATE TABLE relation_tuples (
    object_type      text NOT NULL,
    object_id        text NOT NULL,
    relation         text NOT NULL,
    subject_type     text NOT NULL,
    subject_id       text NOT NULL,
    subject_relation text NOT NULL DEFAULT '',
    CONSTRAINT relation_tuples_pk PRIMARY KEY (object_type, object_id, relation, subject_type, subject_id, subject_relation),
    CONSTRAINT relation_tuples_id_shape CHECK (object_id ~ '^[a-z0-9.-]{1,40}$' AND subject_id ~ '^[a-z0-9.-]{1,40}$'),
    -- Which relations each type of object has.
    CONSTRAINT relation_tuples_relation_for_type CHECK (
           (object_type = 'team' AND relation = 'member')
        OR (object_type = 'folder' AND relation IN ('viewer', 'editor', 'parent'))
        OR (object_type = 'doc' AND relation IN ('owner', 'editor', 'viewer', 'parent'))),
    -- A parent is a folder; anyone else is a user, or every member of a team.
    CONSTRAINT relation_tuples_subject CHECK (
           (relation = 'parent' AND subject_type = 'folder' AND subject_relation = '')
        OR (relation <> 'parent' AND subject_type = 'user' AND subject_relation = '')
        OR (relation <> 'parent' AND subject_type = 'team' AND subject_relation = 'member'))
);
-- A document or folder sits in at most one folder, and has at most one owner.
CREATE UNIQUE INDEX relation_tuples_one_parent ON relation_tuples (object_type, object_id) WHERE relation = 'parent';
CREATE UNIQUE INDEX relation_tuples_one_owner ON relation_tuples (object_type, object_id) WHERE relation = 'owner';
-- "Which objects is this subject related to?": the walk from a user to their teams and their grants.
CREATE INDEX relation_tuples_by_subject ON relation_tuples (subject_type, subject_id, relation);

-- Simulated notification ("ravi shared Brand guidelines with you"), written in the same transaction as the share.
CREATE TABLE share_notices (
    id        bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT share_notices_pk PRIMARY KEY,
    doc_id    text NOT NULL CONSTRAINT share_notices_doc_fk REFERENCES documents ON DELETE CASCADE,
    shared_to text NOT NULL,
    relation  text NOT NULL,
    shared_by text NOT NULL,
    CONSTRAINT share_notices_relation CHECK (relation IN ('viewer', 'editor'))
);
```

# 3 · Go deeper: Production

Depth  
Each level of folders or teams is another step of the walk. Measure checks on the deepest real tree before promising response times.

Caching  
Caching a check brings back the stale-access problem. Zanzibar answers this with consistency tokens; without them, keep caches very short or skip them.

Audit  
Tuples are the permission state: log every write to them (who shared what with whom).

Sources  
"Zanzibar: Google's Consistent, Global Authorization System", USENIX ATC 2019. OpenFGA is a CNCF project; SpiceDB is open source from AuthZed.

# 3 · Go deeper: Interview

## Interview takeaways

What is relationship-based access control?

Access derived from relationships (member of, parent of, viewer of) at check time, instead of permissions stored per resource.

Why do copied permissions go stale?

They record the outcome, not the reason. When the reason (team membership, folder) changes, nothing updates the copies.

What is a userset?

A set of subjects defined by a relation, such as every member of a team, used as one subject in a tuple.

How does the recursive query end?

UNION drops rows already produced, so each object or team is visited once, even if the data has a cycle.

When would you move to OpenFGA or SpiceDB?

When several services need the same checks, trees get deep, or you need expand, caching with consistency and audit out of the box.

## Self-check rubric

| Area        | Meets the bar                     | Above the bar                                          |
|-------------|-----------------------------------|--------------------------------------------------------|
| Correctness | All 18 tests pass.                | You ran the flawed version and explained each failure. |
| Model       | Tuples with teams and folders.    | Teams in teams; constraints per object type.           |
| Checks      | One recursive query.              | Safe against cycles; strongest relation wins.          |
| Change      | Removing a member removes access. | No copies anywhere, including team shares.             |

# 3 · Go deeper: Review

## The pull request

A teammate speeds up checks: a share with a team is written as one row per current member, so "checks need no walk through teams". Viewers may also pass documents on, "as with a link". Read the file and list every problem before opening the findings.

#### `review/Documents.java`

``` code
package com.taskloom.sharing;

import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.security.provisioning.UserDetailsManager;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@Service
class Documents {

    record Doc(String id, String title, String body, String yourAccess) {
    }

    private final JdbcClient jdbc;
    private final Permissions permissions;
    private final UserDetailsManager users;

    Documents(JdbcClient jdbc, Permissions permissions, UserDetailsManager users) {
        this.jdbc = jdbc;
        this.permissions = permissions;
        this.users = users;
    }

    /** No access at all is 404: a document's existence is as private as its text. */
    Doc open(String user, String docId) {
        String access = permissions.access(user, docId).orElseThrow(Documents::notFound);
        return jdbc.sql("SELECT id, title, body FROM documents WHERE id = ?").param(docId)
                .query((rs, n) -> new Doc(rs.getString(1), rs.getString(2), rs.getString(3), access)).single();
    }

    /** Share with a user or a whole team, as viewer or editor, with a notice in the same transaction. */
    @Transactional
    void share(String user, String docId, String subject, String relation) {
        String access = permissions.access(user, docId).orElseThrow(Documents::notFound);
        // Anyone who can open a document may pass it on to a colleague, as with a link.
        String[] s = subject.split(":", 2);
        boolean known = s[0].equals("user") ? users.userExists(s[1])
                : jdbc.sql("SELECT EXISTS (SELECT 1 FROM relation_tuples WHERE object_type = 'team' AND object_id = ?)").param(s[1]).query(Boolean.class).single();
        if (!known) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "No such user or team");
        }
        // A team share is written as one row per member, so checks need no walk through teams.
        List<String> people = s[0].equals("user") ? List.of(s[1])
                : jdbc.sql("SELECT subject_id FROM relation_tuples WHERE object_type = 'team' AND object_id = ? AND relation = 'member' AND subject_type = 'user'")
                        .param(s[1]).query(String.class).list();
        for (String person : people) {
            jdbc.sql("""
                            INSERT INTO relation_tuples (object_type, object_id, relation, subject_type, subject_id, subject_relation)
                            VALUES ('doc', ?, ?, 'user', ?, '') ON CONFLICT DO NOTHING""")
                    .params(docId, relation, person).update();
        }
        jdbc.sql("INSERT INTO share_notices (doc_id, shared_to, relation, shared_by) VALUES (?, ?, ?, ?)").params(docId, subject, relation, user).update();
    }

    static ResponseStatusException notFound() {
        return new ResponseStatusException(HttpStatus.NOT_FOUND, "No such document");
    }
}
```

## Findings

1Team shares copied into member rows

"Checks need no walk through teams" brings the incident back for document shares: whoever leaves the team keeps the document, whoever joins never gets it, and teams inside the team are skipped altogether.

**Test evidence:** `aDocumentSharedWithATeamFollowsTheTeamAfterwards` and `sharingWithATeamReachesEveryMember` (Neha is in a team inside the team) fail.

2Viewers may share

"As with a link": a viewer can now give anyone, or a whole team, the same access, and an editor share needs only viewer rights.

**Test evidence:** `aViewerCannotShareAndAStrangerCannotEvenSee` fails.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed file copied over the real one, then the full suite run.

| Test class                  | Fixed version | Flawed version |
|-----------------------------|---------------|----------------|
| `SharingDatabaseTest`       | 2 / 2         | 2 / 2          |
| `CopiedPermissionsTrapTest` | 4 / 4         | 3 / 4          |
| `SharingContractTest`       | 6 / 6         | 5 / 6          |
| `SharingSecurityTest`       | 6 / 6         | 5 / 6          |

Right after the share, everything looks correct. The flaw appears only when the team changes, which is why the trap tests change teams.
