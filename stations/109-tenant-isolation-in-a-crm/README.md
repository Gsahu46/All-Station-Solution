# Station 109 · Tenant isolation in a CRM

Working Systems · 0–2 years · Core · SaaS · Types: Database, Security

Spring Boot 4.1.1 · Java 25 · Spring Security (HTTP Basic) · JdbcClient · PostgreSQL 17 row-level security · Flyway · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** The companies, people and leads are demo data. Sign-in is a fixed list of demo users; a real identity provider would put the tenant in a signed token.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 11 tests.

# 1 · Understand

## The problem in real life

1.  **Many companies, one CRM**

    Taskloom's CRM keeps sales leads for hundreds of small companies in the same tables, each row marked with its company.

2.  **One forgotten WHERE**

    A new "find lead by email" lookup forgot the company filter. A salesperson at one company saw another company's notes on a shared contact. Elsewhere, an endpoint read the company from the request body: changing one word put a lead into someone else's CRM.

3.  **The fix**

    The company comes from the sign-in only. Every query filters by it, and underneath, the database itself filters by it: a query that forgets returns nothing from anyone else.

Isolation that depends on every developer remembering every WHERE clause will fail once. Put a second guard where nobody can forget it.

## What are we building?

A leads API for many companies at once, where each company sees and writes only its own leads, enforced in the code and in the database.

## An everyday analogy

An apartment block: your key decides which flat you enter, not the number you say at the gate; and even if someone leaves a door open, the lift only stops at your floor.

## How it works in 4 steps

1.  **Sign in**: the user's company is part of their account.
2.  **Open a tenant transaction**: the database is told the company, and switches to the application's limited role.
3.  **Query**: every query filters by the company.
4.  **Underneath**: the database's policy filters again; writes for another company are refused.

Check yourself: if the policy filters anyway, why keep the WHERE clause?

Two guards: the WHERE clause is what developers read and indexes use; the policy catches the day one is missing. Remove either and one mistake is no longer harmless.

## What this station is not

- **No identity provider.** Demo users; the tenant would be a claim in a signed token.
- **No admin view across companies.** That is a separate, audited tool, not a parameter.
- **One tenancy model.** Shared tables; schema or database per tenant are compared in Design.

## Key terms

| Term                      | Simple meaning                                                                    | Everyday example                                         | In this project                  |
|---------------------------|-----------------------------------------------------------------------------------|----------------------------------------------------------|----------------------------------|
| **Tenant**                | One customer company using the shared software, with its own data.                | One flat in an apartment block.                          | `zestful`, `brightpath`          |
| **Multi-tenancy**         | Many customers on one system, each seeing only their own data.                    | One building, many locked flats.                         | shared tables with a `tenant_id` |
| **Tenant from the token** | Which company you are is decided by your sign-in, never by what the request says. | Your key opens your flat; saying a flat number does not. | `SecurityConfig.tenant`          |
| **Row-level security**    | A rule in the database that hides other tenants' rows from every query.           | A lift that only stops at your floor.                    | `leads_tenant_isolation`         |
| **Defence in depth**      | Two independent guards, so one mistake is not a leak.                             | A locked flat in a building with a guard.                | WHERE clause + policy            |
| **Isolation test**        | A test that signs in as one tenant and tries to reach another's data.             | Trying your key in the neighbour's door.                 | `LeadSecurityTest`               |

# 2 · Build: Spec

## Business problem

**Taskloom** (a fictional SaaS company): a missing WHERE clause in its CRM showed one customer company's leads to another.

## Acceptance criteria

1.  **Given** a signed-in user, **then** `GET /leads` lists only their company's leads, filtered by status and text.
2.  **Given** a lead id of another company, **then** `404`, the same as a lead that does not exist.
3.  **Given** `POST /leads` from a salesperson, **then** `201` in their company; an email already a lead of theirs, `409`; the same email at another company is fine.
4.  **Given** a company named in the body or the query string, **then** it is ignored.
5.  **Given** no sign-in, a viewer writing, or bad input, **then** `401`, `403`, `400`.
6.  **Given** any SQL in the application's role, **then** only the transaction's company's rows can be read or written.

## Requirements

- The tenant comes from the sign-in only.
- Every query filters by tenant, and a database policy filters underneath.
- The tenant setting ends with its transaction: a pooled connection never carries it on.

## Learning objectives

- Compare tenancy models: shared tables, schema per tenant, database per tenant.
- Take the tenant from the identity, never the request.
- Use PostgreSQL row-level security with a non-owner role.
- Write isolation tests that try to cross tenants, by API and by SQL.

# 2 · Build: API contract

## Endpoints

| Method | Path                | Who           | Purpose                                                                                          |
|--------|---------------------|---------------|--------------------------------------------------------------------------------------------------|
| `GET`  | `/leads?status=&q=` | sales, viewer | The company's leads, at most 50, newest first; `q` matches name, company or email as plain text. |
| `GET`  | `/leads/{id}`       | sales, viewer | One of the company's leads.                                                                      |
| `POST` | `/leads`            | sales         | `{name, email, company?, status?}`.                                                              |

## Status codes

| Status    | When                                                              |
|-----------|-------------------------------------------------------------------|
| 200 / 201 | Listed / created                                                  |
| 400       | Bad email, unknown status, search text too long                   |
| 401 / 403 | Not signed in / a viewer writing                                  |
| 404       | No such lead in your company (whether or not it exists elsewhere) |
| 409       | Your company already has a lead with this email                   |

## Captured examples

Captured with curl from the running app on 25 Oct 2026, in this order. Ananya and Kabir work at Zestful Foods, Farhan at Brightpath Tutors. `Date`, connection and standard security headers are left out.

### Case 1: Ananya lists her leads

**Why:** Zestful's two.

Request

``` code
GET /leads HTTP/1.1
Authorization: Basic YW5hbnlhOmFuYW55YS1kZW1vLXBhc3M=
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 333

[
  {
    "id": 2,
    "name": "Leela Thomas",
    "email": "leela@greenbowl.example",
    "company": "Green Bowl Cafe",
    "status": "NEW",
    "owner": "ananya",
    "createdAt": "2026-10-25T03:48:54.087647Z"
  },
  {
    "id": 1,
    "name": "Rahul Mehta",
    "email": "rahul@spicehub.example",
    "company": "Spice Hub",
    "status": "QUALIFIED",
    "owner": "ananya",
    "createdAt": "2026-10-25T03:48:54.087647Z"
  }
]
```

### Case 2: Farhan lists his

**Why:** Brightpath's two; Rahul Mehta is a lead of both, as two separate rows.

Request

``` code
GET /leads HTTP/1.1
Authorization: Basic ZmFyaGFuOmZhcmhhbi1kZW1vLXBhc3M=
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 327

[
  {
    "id": 4,
    "name": "Rahul Mehta",
    "email": "rahul@spicehub.example",
    "company": "Spice Hub",
    "status": "NEW",
    "owner": "farhan",
    "createdAt": "2026-10-25T03:48:54.087647Z"
  },
  {
    "id": 3,
    "name": "Sunil Rao",
    "email": "sunil.rao@example.org",
    "company": "Sunrise School",
    "status": "CONTACTED",
    "owner": "farhan",
    "createdAt": "2026-10-25T03:48:54.087647Z"
  }
]
```

### Case 3: Ananya adds a lead

**Why:** `201`; the email lower-cased.

Request

``` code
POST /leads HTTP/1.1
Authorization: Basic YW5hbnlhOmFuYW55YS1kZW1vLXBhc3M=
Content-Type: application/json

{
  "name": "Divya Kapoor",
  "email": "Divya@MasalaBox.example",
  "company": "Masala Box"
}
```

Response

``` code
HTTP/1.1 201 
Location: /leads/5
Content-Type: application/json

{
  "id": 5,
  "name": "Divya Kapoor",
  "email": "divya@masalabox.example",
  "company": "Masala Box",
  "status": "NEW",
  "owner": "ananya",
  "createdAt": "2026-10-25T03:48:56.137135Z"
}
```

### Case 4: the same email again

**Why:** `409`.

Request

``` code
POST /leads HTTP/1.1
Authorization: Basic YW5hbnlhOmFuYW55YS1kZW1vLXBhc3M=
Content-Type: application/json

{
  "name": "Divya K",
  "email": "divya@masalabox.example"
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Your company already has a lead with this email.",
  "instance": "/leads",
  "status": 409,
  "title": "Conflict"
}
```

### Case 5: Farhan adds the same person

**Why:** `201`: unique per company, not across.

Request

``` code
POST /leads HTTP/1.1
Authorization: Basic ZmFyaGFuOmZhcmhhbi1kZW1vLXBhc3M=
Content-Type: application/json

{
  "name": "Divya Kapoor",
  "email": "divya@masalabox.example"
}
```

Response

``` code
HTTP/1.1 201 
Location: /leads/7
Content-Type: application/json

{
  "id": 7,
  "name": "Divya Kapoor",
  "email": "divya@masalabox.example",
  "company": null,
  "status": "NEW",
  "owner": "farhan",
  "createdAt": "2026-10-25T03:48:56.392395Z"
}
```

### Case 6: a body naming Brightpath

**Why:** the body's tenant is not read: the lead is Zestful's (it appears among Zestful's rows in the psql listing below).

Request

``` code
POST /leads HTTP/1.1
Authorization: Basic YW5hbnlhOmFuYW55YS1kZW1vLXBhc3M=
Content-Type: application/json

{
  "tenantId": "brightpath",
  "name": "Planted Lead",
  "email": "planted@example.com"
}
```

Response

``` code
HTTP/1.1 201 
Location: /leads/8
Content-Type: application/json

{
  "id": 8,
  "name": "Planted Lead",
  "email": "planted@example.com",
  "company": null,
  "status": "NEW",
  "owner": "ananya",
  "createdAt": "2026-10-25T03:48:56.495276Z"
}
```

### Case 7: `?tenant=brightpath`

**Why:** ignored: Zestful's Rahul only.

Request

``` code
GET /leads?q=rahul&tenant=brightpath HTTP/1.1
Authorization: Basic YW5hbnlhOmFuYW55YS1kZW1vLXBhc3M=
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 166

[
  {
    "id": 1,
    "name": "Rahul Mehta",
    "email": "rahul@spicehub.example",
    "company": "Spice Hub",
    "status": "QUALIFIED",
    "owner": "ananya",
    "createdAt": "2026-10-25T03:48:54.087647Z"
  }
]
```

### Case 8: Brightpath's lead 3, by id

**Why:** `404`.

Request

``` code
GET /leads/3 HTTP/1.1
Authorization: Basic YW5hbnlhOmFuYW55YS1kZW1vLXBhc3M=
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "instance": "/leads/3",
  "status": 404,
  "title": "Not Found"
}
```

### Case 9: Kabir, a viewer, adds a lead

**Why:** `403`.

Request

``` code
POST /leads HTTP/1.1
Authorization: Basic a2FiaXI6a2FiaXItZGVtby1wYXNz
Content-Type: application/json

{
  "name": "X",
  "email": "x@example.com"
}
```

Response

``` code
HTTP/1.1 403 
Content-Type: application/problem+json
Content-Length: 96

{
  "title": "Not allowed",
  "status": 403,
  "detail": "This sign-in cannot do this.",
  "instance": "/leads"
}
```

### Case 10: no sign-in

**Why:** `401`.

Request

``` code
GET /leads HTTP/1.1
```

Response

``` code
HTTP/1.1 401 
Content-Type: application/problem+json
Content-Length: 108

{
  "title": "Sign-in required",
  "status": 401,
  "detail": "Send a valid username and password.",
  "instance": "/leads"
}
```

### Case 11: searching for %

**Why:** a literal %, not "anything": nothing found.

Request

``` code
GET /leads?q=%25 HTTP/1.1
Authorization: Basic YW5hbnlhOmFuYW55YS1kZW1vLXBhc3M=
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 2

[]
```

### Case 12: a bad email

**Why:** `400`.

Request

``` code
POST /leads HTTP/1.1
Authorization: Basic YW5hbnlhOmFuYW55YS1kZW1vLXBhc3M=
Content-Type: application/json

{
  "name": "X",
  "email": "not-an-email"
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Invalid request content.",
  "instance": "/leads",
  "status": 400,
  "title": "Bad Request"
}
```

## The policy, in psql

The same database, as the application's role, with queries that have no WHERE at all:

``` code
-- as crm_app, no tenant set:
 leads_visible 
---------------
             0
(1 row)

-- as crm_app, tenant zestful:
 tenant  
---------
 zestful
(1 row)

     name     |          email          
--------------+-------------------------
 Rahul Mehta  | rahul@spicehub.example
 Leela Thomas | leela@greenbowl.example
 Divya Kapoor | divya@masalabox.example
 Planted Lead | planted@example.com
(4 rows)

-- as crm_app, tenant zestful, writing a row for brightpath:
 tenant  
---------
 zestful
(1 row)

ERROR:  new row violates row-level security policy for table "leads"
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                                    | What happens                                                                     | Proved by                                                                |
|-------------------------------------------------------------------------|----------------------------------------------------------------------------------|--------------------------------------------------------------------------|
| The old code: tenant from the body; a lookup without tenant             | A lead planted at Brightpath; both companies' rows returned                      | `theOldCodeTrustedTheBodysTenantAndForgotTheTenantInOneQuery`            |
| The API: the same body, a tenant in the query, the same forgetful query | Zestful's lead; Zestful's rows only                                              | `theApiTakesTheTenantFromTheSignInAndTheDatabaseFiltersWhatACodeForgets` |
| Listing and filtering                                                   | Own leads only                                                                   | `aTenantListsAndFiltersItsOwnLeads`                                      |
| Create; duplicate; same email elsewhere                                 | `201`; `409`; `201`                                                              | `aLeadIsCreatedOnceAnEmailPerTenant`                                     |
| Bad input; unknown id                                                   | `400`; `404`                                                                     | `badInputIs400AndAnUnknownLeadIs404`                                     |
| No sign-in; a viewer writing                                            | `401`; `403`                                                                     | `noSignInIs401AndAViewerCannotCreate`                                    |
| Another company's lead by id or search                                  | `404`; not listed                                                                | `anotherTenantsLeadIsNotFoundByIdOrBySearch`                             |
| %, \_, and SQL in the search text                                       | Plain text; nothing extra found                                                  | `searchTextIsTextNotSqlOrAPattern`                                       |
| SQL with no WHERE, as the app's role                                    | Only the transaction's tenant; no tenant, no rows; other tenant's writes refused | `thePolicyShowsAndWritesOnlyTheTransactionsTenant`                       |
| Plain SQL against the rules                                             | Named constraints                                                                | `theRulesAreNamedConstraints`                                            |
| A failed write; pooled connections                                      | Rolled back; the tenant does not stay on the connection                          | `theTenantEndsWithItsTransactionAndAFailedWriteLeavesNothing`            |

## The trap

Plausible but wrong

Taking the tenant id from the request body, or forgetting it in one query.

- **The old way.** The repository took the tenant it was given by the request, and one lookup by email had no tenant at all. Ananya's request plants a lead in Brightpath's CRM, and the lookup returns both companies' rows for Rahul Mehta.
- **The API.** The same body lands in Zestful. A tenant in the query string is ignored. And the very same forgetful lookup, run inside Zestful's transaction, returns Zestful's row only: the policy filtered what the code forgot.

While building, each part was undone once. Removing the WHERE clause alone turned **0** tests red: the policy still filtered every query, which is the point of a second guard, and also why it was undone together with the role switch, which turned 6 red. Then: no role switch alone 2; no tenant setting 7; LIKE wildcards not escaped 1; emails not lower-cased 1; viewers allowed to write 1; a `?tenant=` parameter honoured 1.

``` code
package com.taskloom.crm;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Ananya works at Zestful Foods. Rahul Mehta is a lead of Zestful's and of Brightpath's. Written first. */
class TenantLeakTrapTest extends ApiTest {

    @Autowired
    TenantScope scope;

    /** The old repository: the tenant came in the request, and one lookup forgot it. Ran as the database owner. */
    void oldCreate(String tenantFromBody, String email) {
        jdbc.sql("INSERT INTO leads (tenant_id, name, email, status, owner) VALUES (?, 'Planted Lead', ?, 'NEW', 'ananya')")
                .params(tenantFromBody, email).update();
    }

    List<String> oldFindByEmail(String email) {
        return jdbc.sql("SELECT tenant_id || ':' || company FROM leads WHERE email = ? ORDER BY tenant_id").param(email).query(String.class).list();
    }

    @Test
    void theOldCodeTrustedTheBodysTenantAndForgotTheTenantInOneQuery() {
        oldCreate("brightpath", "planted@example.com");   // Ananya's request, a tenant she typed in
        assertThat(tenantOf("planted@example.com")).isEqualTo("brightpath");
        assertThat(oldFindByEmail("rahul@spicehub.example")).as("Ananya sees Brightpath's notes on the lead")
                .containsExactly("brightpath:Spice Hub", "zestful:Spice Hub");
    }

    @Test
    void theApiTakesTheTenantFromTheSignInAndTheDatabaseFiltersWhatACodeForgets() throws Exception {
        create("ananya", "{\"tenantId\":\"brightpath\",\"name\":\"Planted Lead\",\"email\":\"planted@example.com\"}")
                .andExpect(status().isCreated());
        assertThat(tenantOf("planted@example.com")).isEqualTo("zestful");

        list("ananya", "?q=rahul&tenant=brightpath").andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1)).andExpect(jsonPath("$[0].owner").value("ananya"));

        // The same forgetful query as before, but inside a tenant's transaction: the policy filters it.
        List<String> found = scope.run("zestful", () -> oldFindByEmail("rahul@spicehub.example"));
        assertThat(found).containsExactly("zestful:Spice Hub");
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
./mvnw test                   # all 11 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d --wait
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

Ask the database directly, as the application's role, with and without a tenant:

``` code
docker compose exec postgres psql -U crm -d crm -c "BEGIN; SET LOCAL ROLE crm_app; SELECT count(*) FROM leads; COMMIT;"
docker compose exec postgres psql -U crm -d crm -c "BEGIN; SET LOCAL ROLE crm_app; SELECT set_config('app.tenant','zestful',true); SELECT name FROM leads; COMMIT;"
```

0 rows, then Zestful's. As `crm` (the owner, a superuser) without `SET ROLE`, all four: the policy does not bind superusers, which is why the application must not be one.

## Troubleshooting

| You see                                      | Cause                                                                            | Fix                                                                                 |
|----------------------------------------------|----------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| Every list is empty                          | `app.tenant` not set in the transaction, or set outside it.                      | Run queries through `TenantScope`.                                                  |
| Another company's rows appear                | The connection is a superuser or the table owner, and the role was not switched. | Connect as `crm_app`, or `SET LOCAL ROLE crm_app`; keep `FORCE ROW LEVEL SECURITY`. |
| `new row violates row-level security policy` | A write for a tenant other than the transaction's.                               | The tenant must come from the sign-in.                                              |

## Project layout

``` tree
stations/109-tenant-isolation-in-a-crm/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/taskloom/crm/
│   ├── LeadController.java   ├── Leads.java   ├── TenantScope.java   ├── SecurityConfig.java
│   └── ProblemResponses.java, CrmApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__tenants_and_leads.sql, V2__demo_tenants.sql
├── src/test/java/com/taskloom/crm/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database.

#### `src/main/java/com/taskloom/crm/LeadController.java`

Does  
The endpoints.

Why  
The tenant from the sign-in, every time; validation; email lower-cased with `Locale.ROOT`.

Without it  
A tenant chosen by the caller.

#### `src/main/java/com/taskloom/crm/Leads.java`

Does  
The queries.

Why  
Each says `WHERE tenant_id` and runs inside a tenant transaction; LIKE wildcards in search text are escaped.

Without it  
A lookup that forgets the tenant; a % that matches everything.

#### `src/main/java/com/taskloom/crm/TenantScope.java`

Does  
The tenant transaction.

Why  
`SET LOCAL ROLE crm_app` and `set_config('app.tenant', ..., true)`, then the work.

Without it  
A connection that bypasses the policy; a tenant left on a pooled connection.

- Superusers and table owners skip row-level security. The test database's user is a superuser, so the scope switches to `crm_app`: without that line, 2 tests go red (the policy test and the trap's forgetful query). Production connects as `crm_app` from the start.

#### `src/main/java/com/taskloom/crm/SecurityConfig.java`

Does  
Users and tenants.

Why  
Each user carries a `TENANT_` authority; roles decide reading and writing.

Without it  
A tenant from the request.

- Shortcut: a fixed list of demo users; with an identity provider, the tenant is a claim in the token.

#### `src/main/resources/db/migration/V1__tenants_and_leads.sql`

Does  
Tables, role and policy.

Why  
`tenant_id` on every lead, uniqueness per tenant, `crm_app` without DELETE, and `FORCE ROW LEVEL SECURITY` with USING and WITH CHECK.

Without it  
Any query, from any code, seeing another company.

#### `src/main/resources/db/migration/V2__demo_tenants.sql`

Two companies and their leads, written with each tenant set: the policy applies to migrations too.

#### `src/main/resources/application.yaml`

The database.

#### `compose.yaml`

PostgreSQL 17 for running the app.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class               | Result |
|---------------|-------------------------------------------------------|--------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found              | `LeadContractTest` (3)   | pass   |
| Every station | Reproduce the failure before the fix                  | `TenantLeakTrapTest` (2) | pass   |
| Database      | Rollback and constraint tests against a real database | `LeadDatabaseTest` (3)   | pass   |
| Security      | 401, 403, another user's data, malicious input        | `LeadSecurityTest` (3)   | pass   |

The database tests run plain SQL as `crm_app` with no WHERE at all, so they test the policy, not the Java filters. The tests' own connection is a superuser, which is how they set up and inspect every tenant's rows.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.crm.LeadDatabaseTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.crm.LeadContractTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.crm.LeadSecurityTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.crm.TenantLeakTrapTest
[INFO] Tests run: 11, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/taskloom/crm/TenantLeakTrapTest.java`

Written first: the old repository and the API.

#### `src/test/java/com/taskloom/crm/LeadContractTest.java`

Listing, creating, bad input.

#### `src/test/java/com/taskloom/crm/LeadSecurityTest.java`

Sign-in, roles, other tenants, hostile search text.

#### `src/test/java/com/taskloom/crm/LeadDatabaseTest.java`

The policy and the constraints with plain SQL; a rollback.

#### `src/test/java/com/taskloom/crm/ApiTest.java`

Shared setup.

#### `src/test/java/com/taskloom/crm/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/taskloom/crm/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=LeadStatusChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 11 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 15 tests pass (11 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## Move a lead along

Add `PATCH /leads/{id} {status}` for salespeople: their company's lead only; another company's id is `404` and stays unchanged; a viewer gets `403`.

**Done when:** both tests in `LeadStatusChallengeTest` pass.

Hints

- `UPDATE ... WHERE tenant_id = ? AND id = ? RETURNING ...` inside `TenantScope`: no row means 404.
- The policy would also make another company's row invisible to the UPDATE: try it without the WHERE.

#### `challenge/LeadStatusChallengeTest.java`

``` code
package com.taskloom.crm;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: PATCH /leads/{id} {status}: a salesperson moves their company's lead along; nobody else's. */
class LeadStatusChallengeTest extends ApiTest {

    long id(String tenant, String email) {
        return jdbc.sql("SELECT id FROM leads WHERE tenant_id = ? AND email = ?").params(tenant, email).query(Long.class).single();
    }

    @Test
    void aSalespersonChangesTheirOwnLeadsStatus() throws Exception {
        long lead = id("zestful", "leela@greenbowl.example");
        mvc.perform(patch("/leads/{id}", lead).with(httpBasic("ananya", "ananya-demo-pass")).contentType(MediaType.APPLICATION_JSON)
                .content("{\"status\":\"CONTACTED\"}")).andExpect(status().isOk()).andExpect(jsonPath("$.status").value("CONTACTED"));
        mvc.perform(patch("/leads/{id}", lead).with(httpBasic("ananya", "ananya-demo-pass")).contentType(MediaType.APPLICATION_JSON)
                .content("{\"status\":\"WON\"}")).andExpect(status().isBadRequest());
        mvc.perform(patch("/leads/{id}", lead).with(httpBasic("kabir", "kabir-demo-pass")).contentType(MediaType.APPLICATION_JSON)
                .content("{\"status\":\"LOST\"}")).andExpect(status().isForbidden());
        jdbc.sql("UPDATE leads SET status = 'NEW' WHERE id = ?").param(lead).update();
    }

    @Test
    void anotherTenantsLeadIsNotFoundAndUnchanged() throws Exception {
        long theirs = id("brightpath", "sunil.rao@example.org");
        mvc.perform(patch("/leads/{id}", theirs).with(httpBasic("ananya", "ananya-demo-pass")).contentType(MediaType.APPLICATION_JSON)
                .content("{\"status\":\"LOST\"}")).andExpect(status().isNotFound());
        assertThat(jdbc.sql("SELECT status FROM leads WHERE id = ?").param(theirs).query(String.class).single()).isEqualTo("CONTACTED");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Notes that cannot cross

Add notes: `POST /leads/{id}/notes {text}`. In a new table, with the database guaranteeing a note's tenant is its lead's tenant (`lead_notes_lead_of_same_tenant`) and the same row-level policy as leads.

**Done when:** both tests in `LeadNotesChallengeTest` pass.

Hints

- A foreign key on two columns, `(lead_id, tenant_id)`, needs a UNIQUE on `leads (id, tenant_id)`.
- New tables need their own GRANTs, ENABLE and FORCE, and policy: nothing is inherited.
- A migration of its own: `V3__lead_notes.sql`.

#### `challenge/LeadNotesChallengeTest.java`

``` code
package com.taskloom.crm;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: notes on a lead, in a new table. The note's tenant must be its lead's tenant, in the database: a
 * foreign key on (lead_id, tenant_id), and the same row-level policy as leads.
 */
class LeadNotesChallengeTest extends ApiTest {

    @BeforeEach
    void noNotes() {
        jdbc.sql("DELETE FROM lead_notes").update();
    }

    long id(String tenant, String email) {
        return jdbc.sql("SELECT id FROM leads WHERE tenant_id = ? AND email = ?").params(tenant, email).query(Long.class).single();
    }

    @Test
    void aNoteGoesOnYourOwnLeadOnly() throws Exception {
        mvc.perform(post("/leads/{id}/notes", id("zestful", "rahul@spicehub.example")).with(httpBasic("ananya", "ananya-demo-pass"))
                        .contentType(MediaType.APPLICATION_JSON).content("{\"text\":\"Wants a tasting for 40 people in November.\"}"))
                .andExpect(status().isCreated()).andExpect(jsonPath("$.author").value("ananya"));
        mvc.perform(post("/leads/{id}/notes", id("brightpath", "rahul@spicehub.example")).with(httpBasic("ananya", "ananya-demo-pass"))
                        .contentType(MediaType.APPLICATION_JSON).content("{\"text\":\"Hello\"}"))
                .andExpect(status().isNotFound());
    }

    @Test
    void theDatabaseRefusesANoteWhoseTenantIsNotItsLeads() {
        long theirs = id("brightpath", "sunil.rao@example.org");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO lead_notes (tenant_id, lead_id, author, text) VALUES ('zestful', ?, 'ananya', 'x')")
                .param(theirs).update()).hasMessageContaining("lead_notes_lead_of_same_tenant");
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## "We want our own database"

A large customer asks for its data in a separate database, in a region of its choice. Compare shared tables (this station), a schema per tenant and a database per tenant for this customer and for the hundreds of small ones: isolation, migrations, backups and restores of one tenant, cost, and how the application picks the right connection. Which would you offer, and at what price point?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: the old repository's two mistakes.
2.  Take the tenant from the sign-in; drop it from every request shape.
3.  Filter every query; add the policy, FORCE'd, with a non-owner role.
4.  Test the policy with SQL that has no WHERE.

## Design alternatives and trade-offs

| Model                                              | Isolation                               | Cost and effort                            | Verdict            |
|----------------------------------------------------|-----------------------------------------|--------------------------------------------|--------------------|
| Shared tables + tenant column + row-level security | Good, with two guards                   | Cheapest; one schema to migrate            | Chosen             |
| Shared tables + tenant column only                 | One forgotten WHERE from a leak         | Cheapest                                   | The trap           |
| Schema per tenant                                  | Strong; search_path must be right       | Migrations per schema; hundreds of schemas | Mid-size customers |
| Database per tenant                                | Strongest; separate backups and regions | Most expensive; connection per tenant      | Large customers    |
| Tenant from the request                            | None                                    | None                                       | Never              |

## Database design

| Object                              | What                                                                           | Why                                                                     |
|-------------------------------------|--------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| `leads_tenant_isolation`            | Policy: USING and WITH CHECK `tenant_id = current_setting('app.tenant', true)` | Reads and writes of the transaction's tenant only; no setting, no rows. |
| `FORCE ROW LEVEL SECURITY`          | The policy binds the table owner too                                           | Only superusers and BYPASSRLS roles skip it.                            |
| `crm_app`                           | SELECT, INSERT, UPDATE; no DELETE                                              | The application cannot delete leads at all.                             |
| `leads_email_unique_per_tenant`     | UNIQUE (tenant_id, email)                                                      | Once per company, not across companies.                                 |
| `leads_status`, `tenants_id_format` | CHECKs                                                                         | Known states; clean tenant ids.                                         |

**Transaction boundaries:** every request's database work is one transaction that starts with the role and the tenant (both LOCAL), so neither outlives it.

``` code
-- Every row belongs to one tenant (one Taskloom customer company). Shared tables, a tenant_id column, and the
-- database itself filtering by it (row-level security) under whatever the application forgets.
CREATE TABLE tenants (
    id   TEXT PRIMARY KEY CONSTRAINT tenants_id_format CHECK (id ~ '^[a-z][a-z0-9-]{1,30}$'),
    name TEXT NOT NULL
);

CREATE TABLE leads (
    id         BIGSERIAL PRIMARY KEY,
    tenant_id  TEXT NOT NULL REFERENCES tenants (id),
    name       VARCHAR(100) NOT NULL,
    email      VARCHAR(254) NOT NULL,
    company    VARCHAR(100),
    status     TEXT NOT NULL DEFAULT 'NEW' CONSTRAINT leads_status CHECK (status IN ('NEW', 'CONTACTED', 'QUALIFIED', 'LOST')),
    owner      TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- The same person may be a lead of two companies; within one company, once.
    CONSTRAINT leads_email_unique_per_tenant UNIQUE (tenant_id, email)
);
CREATE INDEX leads_by_tenant ON leads (tenant_id, created_at DESC);

-- The role the application works as. Not the owner and not a superuser, so the policy below applies to it.
DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'crm_app') THEN
        CREATE ROLE crm_app LOGIN PASSWORD 'crm_app';
    END IF;
END $$;
GRANT SELECT ON tenants TO crm_app;
GRANT SELECT, INSERT, UPDATE ON leads TO crm_app;
GRANT USAGE ON SEQUENCE leads_id_seq TO crm_app;

-- Rows of the tenant named in this transaction's app.tenant setting, and no others: for reads, and for writes.
-- No setting means no rows (current_setting(..., true) is NULL).
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads FORCE ROW LEVEL SECURITY;
CREATE POLICY leads_tenant_isolation ON leads
    USING (tenant_id = current_setting('app.tenant', true))
    WITH CHECK (tenant_id = current_setting('app.tenant', true));
```

# 3 · Go deeper: Production

## Real-world considerations

Connection role  
Connect as `crm_app`; run migrations as the owner. Never give the application role BYPASSRLS.

Support access  
When staff must see a customer's data, use a separate tool that sets the tenant from an approved, logged support ticket, never a parameter on the customer API.

Every new table  
Needs its tenant column, its policy and its isolation test. A check in CI that lists tables without a policy catches the one that was forgotten.

Caches and search indexes  
Anything outside the database (caches, search, exports, logs) needs the tenant in its key too; the policy does not reach there.

Performance  
The policy adds a condition the planner uses with `leads_by_tenant`; check plans on the largest tenant.

# 3 · Go deeper: Interview

## Interview takeaways

Where should the tenant id come from?

From the authenticated identity (a claim in the token, or the user's account), never from the body, path or query.

What is row-level security in PostgreSQL?

Policies on a table that add a condition to every query and write; with FORCE, they bind the owner too. Superusers and BYPASSRLS roles skip them.

How do you pass the tenant to the database safely with a pool?

SET LOCAL / set_config(..., true) inside the transaction, so it ends with the transaction.

Shared tables, schema per tenant or database per tenant?

Shared tables for many small tenants; schemas or databases where isolation, regions or per-tenant restores matter enough to pay for.

How do you test isolation?

Sign in as one tenant and try every way to reach another's data, and run SQL without WHERE as the app role.

Why return 404, not 403, for another tenant's id?

403 confirms the id exists; 404 tells nothing.

## Self-check rubric

| Area           | Meets the bar         | Above the bar                                                             |
|----------------|-----------------------|---------------------------------------------------------------------------|
| Correctness    | All 11 tests pass.    | You ran the flawed version and explained each failure.                    |
| Tenant source  | From the sign-in.     | No request field can name a tenant, and a test proves it.                 |
| Isolation      | WHERE on every query. | A FORCE'd policy under it, a non-owner role, and SQL tests without WHERE. |
| Tenancy models | Knows shared tables.  | Can argue schema or database per tenant for a given customer.             |

# 3 · Go deeper: Review

## The pull request

A teammate "simplifies" the scope and adds a support feature: "the WHERE clauses already isolate tenants, and support needs to switch companies". Read both files and list every problem before opening the findings.

#### `review/TenantScope.java`

``` code
package com.taskloom.crm;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.function.Supplier;

/**
 * Runs work in a transaction with app.tenant set. Switching roles is not needed: every query in Leads already says
 * WHERE tenant_id = :tenant.
 */
@Component
class TenantScope {

    private final JdbcClient jdbc;
    private final TransactionTemplate tx;

    TenantScope(JdbcClient jdbc, TransactionTemplate tx) {
        this.jdbc = jdbc;
        this.tx = tx;
    }

    <T> T run(String tenant, Supplier<T> work) {
        return tx.execute(status -> {
            jdbc.sql("SELECT set_config('app.tenant', ?, true)").param(tenant).query().singleValue();
            return work.get();
        });
    }
}
```

#### `review/LeadController.java`

``` code
package com.taskloom.crm;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.util.List;
import java.util.Locale;

/** The tenant comes from the sign-in, or from ?tenant= when someone needs another company's view. */
@RestController
class LeadController {

    static final String STATUSES = "NEW|CONTACTED|QUALIFIED|LOST";

    record NewLead(@NotBlank @Size(max = 100) String name, @NotBlank @Email @Size(max = 254) String email,
                   @Size(max = 100) String company, @Pattern(regexp = STATUSES) String status) {
    }

    private final Leads leads;

    LeadController(Leads leads) {
        this.leads = leads;
    }

    @GetMapping("/leads")
    List<Leads.Lead> search(Authentication user, @RequestParam(required = false) @Pattern(regexp = STATUSES) String status,
                            @RequestParam(required = false) @Size(min = 1, max = 100) String q,
                            @RequestParam(required = false) String tenant) {
        // Support staff look at customers' CRMs: ?tenant= lets them switch company; everyone else gets their own.
        return leads.search(tenant != null ? tenant : SecurityConfig.tenant(user), status, q);
    }

    @GetMapping("/leads/{id}")
    Leads.Lead lead(Authentication user, @PathVariable long id) {
        return leads.find(SecurityConfig.tenant(user), id).orElseThrow(() -> new ErrorResponseException(HttpStatus.NOT_FOUND));
    }

    @PostMapping("/leads")
    ResponseEntity<Leads.Lead> create(Authentication user, @Valid @RequestBody NewLead body) {
        Leads.Lead lead = leads.create(SecurityConfig.tenant(user), body.name().strip(), body.email().strip().toLowerCase(Locale.ROOT),
                body.company() == null || body.company().isBlank() ? null : body.company().strip(),
                body.status() == null ? "NEW" : body.status(), user.getName());
        return ResponseEntity.created(URI.create("/leads/" + lead.id())).body(lead);
    }

    @ExceptionHandler(Leads.EmailTaken.class)
    ProblemDetail emailTaken() {
        return ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, "Your company already has a lead with this email.");
    }
}
```

## Findings

1The policy switched off without anyone noticing

"Switching roles is not needed: every query already says WHERE tenant_id": the connection is the owner's, which the policy does not bind, so the second guard is gone. Nothing fails today; the next forgotten WHERE is a leak again.

**Test evidence:** `thePolicyShowsAndWritesOnlyTheTransactionsTenant` fails: as the owner, a write for Brightpath inside Zestful's transaction goes through.

2A tenant from the query string

"Support staff look at customers' CRMs: ?tenant= lets them switch company": so can every customer. Any salesperson can add `?tenant=` and read another company's leads.

**Test evidence:** `theApiTakesTheTenantFromTheSignInAndTheDatabaseFiltersWhatACodeForgets` fails: `?tenant=brightpath` returns Brightpath's lead.

## Same tests, flawed version

From `docs/review-run.txt`: the flawed files copied over the real ones, then the full suite run.

| Test class           | Fixed version | Flawed version |
|----------------------|---------------|----------------|
| `LeadContractTest`   | 3 / 3         | 3 / 3          |
| `LeadSecurityTest`   | 3 / 3         | 3 / 3          |
| `LeadDatabaseTest`   | 3 / 3         | 2 / 3          |
| `TenantLeakTrapTest` | 2 / 2         | 1 / 2          |

Every listing in the flawed version is still correct for every user who does not type `?tenant=`. That is what makes both mistakes easy to merge.
