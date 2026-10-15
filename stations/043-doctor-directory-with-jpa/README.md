# Station 043 · Doctor directory with JPA

Foundations · 0–1 years · Core · Healthcare · Types: Database

Spring Boot 4.1.1 · Java 25 · Spring Data JPA · Hibernate 7 · @Entity, JpaRepository, derived queries, @EntityGraph · DTO records · PostgreSQL 17 · Flyway · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Doctors, clinics, phone numbers, salaries and notes are fictional demo data. The private columns exist so the trap test can show what leaks.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 11 tests.

# 1 · Understand

## The problem in real life

1.  **A week per filter**

    Every doctor search was SQL written by hand. Adding "speciality" meant new SQL, new mapping, new tests: a week.

2.  **JPA, returned as is**

    The team switched to JPA and returned the Doctor entity straight from the controller. Some requests failed with a lazy-loading error. The others sent each doctor's personal phone, salary and HR notes to every visitor of the public directory.

3.  **The fix**

    Entities stay inside the service. The API returns a small record with only what the directory shows, built while the database session is open.

The API's shape is a decision. Never let it be whatever the table happens to hold.

## What are we building?

`GET /doctors?speciality=…&city=…` searches the public directory, and `GET /doctors/{id}` shows one doctor: name, speciality, city, registration number and clinic.

## An everyday analogy

A hospital's notice board shows each doctor's name, speciality and room. The HR file with salary and home phone stays in the office. You copy what the board needs onto the board; you do not pin up the file.

## How it works in 4 steps

1.  **Pick a repository method** for the filters given; Spring Data has written its query.
2.  **Load doctors and their clinics** in one query.
3.  **Copy each into a `DoctorView`**, inside the transaction.
4.  **Return the views**; the entities never reach the JSON writer.

Check yourself: if the entity has a `@JsonIgnore` on salary, is returning it fine?

Safer, but fragile: the next private column added to the table is public until someone remembers to hide it, and the lazy clinic can still fail. A DTO lists what is public; everything else is private by default.

## What this station is not

- **Read-only.** No adding or editing doctors here.
- **No appointments.** Just the directory.
- **No full-text search.** Exact speciality and city, any letter case.

## Key terms

| Term              | Simple meaning                                                                              | Everyday example                                                        | In this project                      |
|-------------------|---------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|--------------------------------------|
| **JPA**           | A standard way to map Java classes to tables, so you work with objects instead of SQL rows. | A translator between your language and the database's.                  | `jakarta.persistence`                |
| **Entity**        | A class whose objects are rows of a table, managed by Hibernate.                            | A file card that is also the record in the cabinet.                     | `Doctor`                             |
| **Repository**    | An interface; Spring Data writes the code behind it.                                        | Asking the librarian instead of searching the shelves.                  | `DoctorRepository`                   |
| **Derived query** | A query written from a method's name.                                                       | "Find by speciality and city, ordered by name".                         | `findBySpecialityIgnoreCaseAndCity…` |
| **DTO**           | A plain object shaped for the API, separate from the entity.                                | The visiting card, not the HR file.                                     | `DoctorView`                         |
| **Lazy loading**  | A linked object is fetched only when first touched, while the session is open.              | A file fetched from storage when you ask, if the archive is still open. | `Doctor.clinic`                      |

# 2 · Build: Spec

## Business problem

**Mediqo** (a fictional clinic chain) wrote SQL by hand for every doctor search; adding a speciality filter took a week.

## Acceptance criteria

1.  **Given** `speciality=cardiology&city=PUNE`, **then** Dr Asha Mehta and Dr Fatima Ali, by name.
2.  **Given** only a speciality, only a city, or neither, **then** the matching doctors; a speciality nobody has, an empty list.
3.  **Given** doctor 1, **then** exactly id, name, speciality, city, registration number, clinic and clinic address; no personal phone, salary or notes anywhere.
4.  **Given** a search of all doctors, **then** one database query, not one more per clinic.
5.  **Given** an unknown doctor, `404`; a filter with digits or over 40 characters, or a non-numeric id, `400`.

## Requirements

- Entities never leave the service; the API returns `DoctorView`.
- `open-in-view` is off: no database access while JSON is written.
- Flyway owns the schema; Hibernate only validates it.
- Rules stay database constraints too: unique registration number, valid clinic, positive salary.

## Learning objectives

- Map tables with `@Entity`, `@Id` and `@ManyToOne`.
- Use `JpaRepository` and derived query methods.
- Separate entities from DTOs, and say why.
- Explain lazy loading, `open-in-view`, and N+1 queries.

# 2 · Build: API contract

## Endpoints

| Method | Path                           | Purpose                                                           |
|--------|--------------------------------|-------------------------------------------------------------------|
| `GET`  | `/doctors?speciality=…&city=…` | Doctors in the directory; both filters optional, any letter case. |
| `GET`  | `/doctors/{id}`                | One doctor.                                                       |

## Status codes

| Status | When                                                                 |
|--------|----------------------------------------------------------------------|
| 200    | A list (possibly empty) or one doctor                                |
| 400    | A filter that is not 2 to 40 letters and spaces, or a non-numeric id |
| 404    | No such doctor                                                       |

## Captured examples

Captured with curl from the running app on 15 Oct 2026. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: cardiology in Pune

**Why:** a derived query with two IgnoreCase conditions.

Request

``` code
GET /doctors?speciality=cardiology&city=pune HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 391

[
  {
    "id": 1,
    "name": "Dr Asha Mehta",
    "speciality": "Cardiology",
    "city": "Pune",
    "registrationNumber": "MMC-2011-04512",
    "clinic": "Mediqo Koregaon Park",
    "clinicAddress": "Lane 5, Koregaon Park, Pune 411001"
  },
  {
    "id": 5,
    "name": "Dr Fatima Ali",
    "speciality": "Cardiology",
    "city": "Pune",
    "registrationNumber": "MMC-2020-09045",
    "clinic": "Mediqo Koregaon Park",
    "clinicAddress": "Lane 5, Koregaon Park, Pune 411001"
  }
]
```

### Case 2: cardiology anywhere

**Why:** another derived method; each doctor's clinic came in the same query.

Request

``` code
GET /doctors?speciality=Cardiology HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 599

[
  {
    "id": 1,
    "name": "Dr Asha Mehta",
    "speciality": "Cardiology",
    "city": "Pune",
    "registrationNumber": "MMC-2011-04512",
    "clinic": "Mediqo Koregaon Park",
    "clinicAddress": "Lane 5, Koregaon Park, Pune 411001"
  },
  {
    "id": 5,
    "name": "Dr Fatima Ali",
    "speciality": "Cardiology",
    "city": "Pune",
    "registrationNumber": "MMC-2020-09045",
    "clinic": "Mediqo Koregaon Park",
    "clinicAddress": "Lane 5, Koregaon Park, Pune 411001"
  },
  {
    "id": 4,
    "name": "Dr Kabir Khan",
    "speciality": "Cardiology",
    "city": "Bengaluru",
    "registrationNumber": "KMC-2018-02290",
    "clinic": "Mediqo Indiranagar",
    "clinicAddress": "100 Feet Road, Indiranagar, Bengaluru 560038"
  }
]
```

### Case 3: doctor 1

**Why:** the view: what the directory shows, nothing else.

Request

``` code
GET /doctors/1 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 194

{
  "id": 1,
  "name": "Dr Asha Mehta",
  "speciality": "Cardiology",
  "city": "Pune",
  "registrationNumber": "MMC-2011-04512",
  "clinic": "Mediqo Koregaon Park",
  "clinicAddress": "Lane 5, Koregaon Park, Pune 411001"
}
```

### Case 4: doctor 99

**Why:** `404`.

Request

``` code
GET /doctors/99 HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No doctor 99.",
  "instance": "/doctors/99",
  "status": 404,
  "title": "Doctor not found"
}
```

### Case 5: `Cardio1ogy`

**Why:** `400`, before the database.

Request

``` code
GET /doctors?speciality=Cardio1ogy HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "Validation failure",
  "instance": "/doctors",
  "status": 400,
  "title": "Bad Request"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                                  | What happens                                        | Proved by                                 |
|-----------------------------------------------------------------------|-----------------------------------------------------|-------------------------------------------|
| Both filters, mixed case                                              | Two doctors, by name                                | `bothFiltersInAnyCase`                    |
| One filter; none; nobody matches                                      | The right doctors; all six; empty                   | `oneFilterOrNone`                         |
| One doctor; any list                                                  | Exactly the view's fields; no phone digits anywhere | `oneDoctorAsTheDirectoryShowsThem`        |
| Searching every doctor                                                | 1 query (3 without the entity graph)                | `aSearchLoadsDoctorsAndClinicsInOneQuery` |
| Duplicate registration, unknown clinic, zero salary, written directly | Refused by named constraints                        | `namedConstraintsHoldWithoutJava`         |
| An import with a duplicate                                            | Rolled back                                         | `aFailedImportLeavesTheDirectoryAsItWas`  |
| Unknown doctor; bad filters or id                                     | `404`; `400`                                        | `DoctorContractTest`                      |

## The trap

Plausible but wrong

Returning entities directly as JSON, leaking fields and lazy-loading errors.

The test writes a `Doctor` entity with the app's own JSON mapper (Jackson 3), as the old controller did. Outside a transaction (open-in-view off), the lazy clinic cannot be loaded: `LazyInitializationException … no session`. Inside one (what open-in-view on would do), the JSON contains `personalPhone`, `salaryPaise`, `internalNotes`, and Hibernate's own `hibernateLazyInitializer`. A probe while building found a third outcome. With package-private getters on `Clinic`, the proxy was written as `{"hibernateLazyInitializer":{}}` with no error at all. Entities usually have public getters, so this station uses them and shows the two common outcomes. While building, adding the personal phone to the view turned 2 tests red. Removing the entity graph from the full list turned 1 red: 3 queries instead of 1.

``` code
package com.mediqo.doctors;

import org.hibernate.LazyInitializationException;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;
import tools.jackson.databind.json.JsonMapper;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The first test written for this station: what the old controller did, returning the Doctor entity as JSON, with
 * the app's own JSON mapper. Two outcomes, both bad, depending on whether a transaction is still open.
 */
class EntityAsJsonTrapTest extends ApiTest {

    @Autowired
    JsonMapper json;
    @Autowired
    TransactionTemplate transaction;
    @Autowired
    DoctorDirectory directory;

    @Test
    void outsideATransactionTheLazyClinicCannotBeLoaded() {
        Doctor doctor = doctors.findById(1L).orElseThrow();   // the clinic is a placeholder until touched
        assertThatThrownBy(() -> json.writeValueAsString(doctor))
                .hasRootCauseInstanceOf(LazyInitializationException.class)
                .hasMessageContaining("no session");
    }

    @Test
    void insideOneEveryPrivateColumnLeaks() {
        // What open-in-view=true would have done: the session stays open while the JSON is written.
        String body = transaction.execute(status -> json.writeValueAsString(doctors.findById(1L).orElseThrow()));
        assertThat(body).contains("\"personalPhone\":\"90000 10001\"", "\"salaryPaise\":45000000",
                "\"internalNotes\":\"On notice period until December\"", "hibernateLazyInitializer");
    }

    @Test
    void theViewHasOnlyWhatTheDirectoryShows() {
        String body = json.writeValueAsString(directory.one(1L).orElseThrow());
        assertThat(body).doesNotContain("personalPhone", "salary", "internalNotes", "hibernate")
                .contains("\"clinic\":\"Mediqo Koregaon Park\"");
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
./mvnw test                 # all 11 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

See the SQL Spring Data writes for a method name. Start the app with SQL logging on, then search:

``` code
./mvnw spring-boot:run -Dspring-boot.run.arguments=--logging.level.org.hibernate.SQL=debug
curl "http://localhost:8080/doctors?speciality=cardiology&city=pune"
```

The log shows one `select … from doctors … join clinics …` with `upper(…)` on both filters.

## Troubleshooting

| You see                                                                | Cause                                                | Fix                                                                        |
|------------------------------------------------------------------------|------------------------------------------------------|----------------------------------------------------------------------------|
| `LazyInitializationException: Could not initialize proxy … no session` | A lazy link was touched after the transaction ended. | Map to a DTO inside the transaction, or load the link with `@EntityGraph`. |
| `Schema-validation: missing column`                                    | An entity field has no matching column.              | Add a Flyway migration; `ddl-auto: validate` never changes the schema.     |
| `No property 'specialty' found for type 'Doctor'`                      | A derived method name does not match a field.        | Method names must spell the field exactly.                                 |
| `Could not find a valid Docker environment`                            | Docker is not running.                               | Start Docker, then run the tests again.                                    |

## Project layout

``` tree
stations/043-doctor-directory-with-jpa/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/mediqo/doctors/
│   ├── DoctorController.java   ├── DoctorDirectory.java   ├── DoctorRepository.java
│   ├── DoctorView.java   ├── Doctor.java   ├── Clinic.java   └── DoctorsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__clinics_and_doctors.sql, V2__demo_directory.sql
├── src/test/java/com/mediqo/doctors/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the entities and the database.

#### `src/main/java/com/mediqo/doctors/DoctorController.java`

Does  
Validates the filters and returns views.

Why  
It never sees an entity.

Without it  
Returning `Doctor`: the trap.

#### `src/main/java/com/mediqo/doctors/DoctorDirectory.java`

Does  
Chooses the repository method and maps to `DoctorView`.

Why  
`@Transactional(readOnly = true)`: the mapping runs while the session is open.

Without it  
Mapping in the controller after the session closed: lazy-loading errors.

#### `src/main/java/com/mediqo/doctors/DoctorRepository.java`

Does  
Derived query methods, each with an entity graph.

Why  
A new filter is a new method name; `@EntityGraph` joins the clinic so there is one query.

Without it  
One query for doctors plus one per clinic (N+1).

- `IgnoreCase` becomes `upper(…) = upper(…)` in SQL.
- `findWithClinicById`: words between `find` and `By` are free text, so the method can be named for what it does.

#### `src/main/java/com/mediqo/doctors/DoctorView.java`

Does  
What the directory shows.

Why  
Fields are listed on purpose; new private columns stay private.

Without it  
Every column of the table in the public API.

#### `src/main/java/com/mediqo/doctors/Doctor.java`

Does  
The doctors table as an entity, with a lazy link to the clinic.

Why  
Hibernate tracks and loads it; `protected` no-argument constructor for JPA.

Without it  
Nothing to map rows to.

#### `src/main/java/com/mediqo/doctors/Clinic.java`

The clinics table as an entity.

#### `src/main/resources/db/migration/V1__clinics_and_doctors.sql`

Both tables, named constraints, and an index for the search.

#### `src/main/resources/db/migration/V2__demo_directory.sql`

Two clinics and six doctors.

#### `src/main/resources/application.yaml`

`open-in-view: false` and `ddl-auto: validate`, with why.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/mediqo/doctors/DoctorsApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                 | Result |
|---------------|-------------------------------------------------------|----------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found              | `DoctorContractTest` (5)   | pass   |
| Every station | Reproduce the failure before the fix                  | `EntityAsJsonTrapTest` (3) | pass   |
| Database      | Rollback and constraint tests against a real database | `DoctorDatabaseTest` (3)   | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, Hibernate 7, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.doctors.DoctorDatabaseTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.doctors.EntityAsJsonTrapTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.doctors.DoctorContractTest
[INFO] Tests run: 11, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/mediqo/doctors/EntityAsJsonTrapTest.java`

Written first: the entity as JSON outside and inside a transaction, and the view.

#### `src/test/java/com/mediqo/doctors/DoctorContractTest.java`

Searches, one doctor, and refusals through HTTP.

#### `src/test/java/com/mediqo/doctors/DoctorDatabaseTest.java`

Named constraints, a rollback, and the query count from Hibernate's statistics.

#### `src/test/java/com/mediqo/doctors/ApiTest.java`

Shared setup, with Hibernate statistics on.

#### `src/test/java/com/mediqo/doctors/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/mediqo/doctors/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=ClinicDoctorsChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 11 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 14 tests pass (11 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## A clinic's doctors

Add `GET /clinics/{id}/doctors`: the clinic's doctors by name, as views. An unknown clinic is `404`, not an empty list.

**Done when:** both tests in `ClinicDoctorsChallengeTest` pass.

Hints

- A derived query can follow the link: `findByClinicIdOrderByName`.
- A small `ClinicRepository` gives you `existsById` for the 404.

#### `challenge/ClinicDoctorsChallengeTest.java`

``` code
package com.mediqo.doctors;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /clinics/{id}/doctors lists a clinic's doctors by name, as DoctorView. A derived query can follow
 * the link to the clinic: findByClinicId… An unknown clinic is 404, not an empty list.
 */
class ClinicDoctorsChallengeTest extends ApiTest {

    @Test
    void aClinicListsItsDoctors() throws Exception {
        mvc.perform(get("/clinics/2/doctors")).andExpect(status().isOk())
                .andExpect(jsonPath("$[*].name", contains("Dr John Dsouza", "Dr Kabir Khan", "Dr Meena Rao")))
                .andExpect(jsonPath("$[0].clinic").value("Mediqo Indiranagar"));
    }

    @Test
    void anUnknownClinicIs404() throws Exception {
        mvc.perform(get("/clinics/9/doctors")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 25 minutes

## Doctors per speciality

Add `GET /specialities`: each speciality and its number of doctors, most first, then by name, counted by the database.

**Done when:** the test in `SpecialityCountChallengeTest` passes.

Hints

- A JPQL `@Query` with `group by` and aliases.
- An interface projection (`getSpeciality()`, `getDoctors()`) receives the aliased columns.

#### `challenge/SpecialityCountChallengeTest.java`

``` code
package com.mediqo.doctors;

import org.junit.jupiter.api.Test;
import org.springframework.test.json.JsonCompareMode;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;

/**
 * Challenge 2: GET /specialities: each speciality with how many doctors, most first, then by name. Count in the
 * database with a JPQL query and a projection, not by loading every doctor into Java.
 */
class SpecialityCountChallengeTest extends ApiTest {

    @Test
    void specialitiesWithTheirDoctorCounts() throws Exception {
        mvc.perform(get("/specialities")).andExpect(content().json("""
                [{"speciality":"Cardiology","doctors":3},{"speciality":"Dermatology","doctors":1},
                 {"speciality":"Orthopaedics","doctors":1},{"speciality":"Paediatrics","doctors":1}]""", JsonCompareMode.STRICT));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## When method names stop scaling

Product wants filters for speciality, city, language spoken, gender, fee range and availability, in any combination. Derived methods would need 64 names. Compare JPA Specifications, Querydsl, Query by Example and a hand-written SQL builder with parameters. Which keeps queries type-safe, which keeps them readable, and which makes indexes easy to plan?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the schema in Flyway; set Hibernate to validate it.
2.  Write the entities and the repository's derived methods.
3.  Write the trap test: the entity as JSON, in and out of a transaction.
4.  Write the view and the service that maps inside a transaction; count the queries.

## Design alternatives and trade-offs

| Approach                                           | What it costs                                                                                 | Verdict                      |
|----------------------------------------------------|-----------------------------------------------------------------------------------------------|------------------------------|
| Entities in the service, DTO records in the API    | A small mapping per view.                                                                     | Chosen                       |
| Return entities, hide fields with `@JsonIgnore`    | New columns are public by default; lazy links still fail.                                     | Fragile                      |
| `open-in-view: true`                               | Lazy links load during JSON writing: hidden queries, connections held for the whole response. | Hides problems               |
| `FetchType.EAGER` on the clinic                    | Every load of a doctor loads the clinic, wanted or not.                                       | Rarely right                 |
| Interface projections straight from the repository | No entity at all for read-only views.                                                         | Good for reads (challenge 2) |

## Database design

| Table     | Key and constraints                                                                                                               | Mapped as                                                |
|-----------|-----------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------|
| `clinics` | PK `id`                                                                                                                           | `@Entity Clinic`                                         |
| `doctors` | PK `id`, `doctors_registration_unique`, `doctors_clinic_fk`, `doctors_salary_positive`; index on `upper(speciality), upper(city)` | `@Entity Doctor`, `@ManyToOne(fetch = LAZY)` to `Clinic` |

The index uses `upper()` because that is what the generated SQL compares (see Set up & code); an index on `lower()`, the first version, could never have been used. Hibernate maps `registrationNumber` to `registration_number` by Spring Boot's naming strategy. `ddl-auto: validate` stops the app at startup if they ever disagree.

``` code
CREATE TABLE clinics (
    id      BIGINT       PRIMARY KEY,
    name    VARCHAR(80)  NOT NULL,
    city    VARCHAR(40)  NOT NULL,
    address VARCHAR(200) NOT NULL
);

CREATE TABLE doctors (
    id                  BIGINT       PRIMARY KEY,
    name                VARCHAR(80)  NOT NULL,
    speciality          VARCHAR(40)  NOT NULL,
    city                VARCHAR(40)  NOT NULL,
    registration_number VARCHAR(20)  NOT NULL,   -- public: printed on prescriptions
    personal_phone      VARCHAR(15)  NOT NULL,   -- private: for the clinic only
    salary_paise        BIGINT       NOT NULL,   -- private
    internal_notes      VARCHAR(500),            -- private
    clinic_id           BIGINT       NOT NULL,
    CONSTRAINT doctors_registration_unique UNIQUE (registration_number),
    CONSTRAINT doctors_clinic_fk           FOREIGN KEY (clinic_id) REFERENCES clinics (id),
    CONSTRAINT doctors_salary_positive     CHECK (salary_paise > 0)
);
-- upper(), because Spring Data writes IgnoreCase as upper(column) = upper(?): an index on lower() would never be used.
CREATE INDEX doctors_speciality_city ON doctors (upper(speciality), upper(city));
```

# 3 · Go deeper: Production

Data exposure  
A leaked column is a data breach. Review API responses as carefully as SQL: what fields leave the server?

Query counts  
N+1 queries are invisible in development and painful in production. Count queries in tests, as this station does, for pages that list things.

open-in-view  
Spring Boot enables it by default and logs a warning at startup. Turning it off early is easy; turning it off late breaks code that relied on it.

Schema ownership  
Flyway changes the schema; `ddl-auto: validate` only checks. Never let Hibernate create or update production tables.

# 3 · Go deeper: Interview

## Interview takeaways

Why not return JPA entities from a REST controller?

They expose every mapped column, including private ones, tie the API to the table, and can trigger lazy loading (extra queries or LazyInitializationException) while JSON is written. Return DTOs.

What is open-in-view, and why turn it off?

It keeps the persistence session open until the response is written, so lazy links load in the view layer. That hides N+1 queries and holds a connection for the whole request. Off makes problems visible.

What is the N+1 problem?

One query for a list, then one more per item to load a link. Fix it with a fetch join or an entity graph.

How do derived query methods work?

Spring Data parses the method name (findBy + properties + keywords like IgnoreCase, OrderBy) and generates the query at startup; a misspelt property fails startup.

Entity vs DTO?

An entity is a managed row: identity, lazy links, change tracking. A DTO is a plain value shaped for one use, such as an API response.

## Self-check rubric

| Area        | Meets the bar                          | Above the bar                            |
|-------------|----------------------------------------|------------------------------------------|
| Correctness | All 11 tests pass.                     | You logged the SQL for a derived method. |
| JPA         | Entities, repository, derived queries. | Entity graphs and query counting.        |
| API design  | DTOs, never entities.                  | Why @JsonIgnore is not enough.           |
| Sessions    | open-in-view off.                      | Exactly when a lazy link can be loaded.  |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any JPA endpoint:

- Does any controller return an `@Entity`?
- Is `open-in-view` off, and does the mapping happen inside a transaction?
- How many queries does the list endpoint run for 50 items?
- Does Hibernate validate the schema, or change it?
