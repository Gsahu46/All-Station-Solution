# Station 041 · Clinic appointments report with joins

Foundations · 0–1 years · Core · Healthcare · Types: Database

Spring Boot 4.1.1 · Java 25 · PostgreSQL 17: INNER and LEFT JOIN, GROUP BY, HAVING, FILTER, COALESCE · JdbcClient · Flyway · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Doctors, patients, fees and appointments are demo data for one week, not Mediqo's. The report reads records only.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 11 tests.

# 1 · Understand

## The problem in real life

1.  **A weekly report**

    Every Monday, the clinic head reads how many patients each doctor saw last week.

2.  **Two doctors are wrong**

    Dr Khan joined last week and saw nobody yet. He is missing from the report altogether, so nobody notices he is idle. Dr Mehta shows 4 appointments, though he saw 3: one patient had two follow-ups booked, and the report counted that visit twice.

3.  **The fix**

    Start from every doctor, attach their appointments if there are any, count appointments themselves, and count follow-ups separately.

A report should show zero as zero, not leave it out, and count each thing once.

## What are we building?

`GET /reports/doctor-load?from=…&to=…` lists every active doctor with the appointments, completed visits, no-shows, follow-ups and fees of those days, busiest first.

## An everyday analogy

A school attendance register. It lists every student, and an absent student gets a 0, not a missing line. If one student brought two notes, they are still one student.

## How it works in 4 steps

1.  **Start from every active doctor.**
2.  **Attach appointments** in the range, if any (LEFT JOIN, the range in the join condition).
3.  **Attach follow-up counts**, already totalled per appointment, so no row repeats.
4.  **Count per doctor**, turning "no fees" (NULL) into 0.

Check yourself: the LEFT JOIN is in place, but the query still says `WHERE a.starts_at >= '2026-10-05'`. Does Dr Khan appear?

No. For Dr Khan, `a.starts_at` is NULL, and `NULL >= date` is not true, so WHERE removes his row. The condition belongs in the JOIN's ON clause.

## What this station is not

- **No booking.** A read-only report.
- **No charts.** JSON rows; a dashboard reads them.
- **One clinic.** Many clinics over a year is challenge 3.

## Key terms

| Term           | Simple meaning                                                       | Everyday example                                                | In this project               |
|----------------|----------------------------------------------------------------------|-----------------------------------------------------------------|-------------------------------|
| **JOIN**       | Combine rows from two tables that match on a condition.              | Matching a class list with an exam results list by roll number. | `doctors` with `appointments` |
| **INNER JOIN** | Keep only rows that have a match on both sides.                      | Only students who sat the exam appear.                          | the trap                      |
| **LEFT JOIN**  | Keep every row on the left, matched or not; missing values are NULL. | Every student appears; absentees get a blank.                   | `DoctorLoadReport`            |
| **GROUP BY**   | Collapse rows into one per group, with totals.                       | One line per doctor.                                            | `GROUP BY d.id`               |
| **HAVING**     | A condition on the groups, after counting.                           | "Only doctors with at least 2 appointments".                    | `minAppointments`             |
| **NULL**       | "No value": not zero, and any comparison with it is not true.        | A blank cell, not a 0.                                          | `coalesce(sum(…), 0)`         |

# 2 · Build: Spec

## Business problem

**Mediqo** (a fictional clinic chain) gets a weekly report that hides doctors with zero appointments and double-counts appointments that have follow-ups.

## Acceptance criteria

On the demo week, 5 to 11 October 2026.

1.  **Given** the week, **then** Dr Mehta 3, Dr Iyer 2, Dr Rao 1, Dr Khan 0, in that order; the retired Dr Das is not listed.
2.  **Given** Dr Mehta's appointment with two follow-ups, **then** it counts once as an appointment, and his follow-ups total 3.
3.  **Given** a cancelled appointment, **then** it is not counted; fees count only completed visits.
4.  **Given** Sunday 11 October only, **then** Dr Iyer's 23:30 appointment is in, and Dr Rao's at 00:15 on Monday is not.
5.  **Given** `minAppointments=2`, **then** only Dr Mehta and Dr Iyer.
6.  **Given** a week with no appointments, **then** every active doctor at zero. **Given** `to` before `from`, more than 92 days, or a missing or malformed date, `400`.

## Requirements

- Every active doctor appears, whatever the range holds.
- Days are India days; `from` and `to` are both included.
- No count is inflated by a one-to-many join.
- Money in integer paise; no NULL in the output.

## Learning objectives

- Choose INNER or LEFT JOIN, and put conditions in ON or WHERE on purpose.
- Use GROUP BY, HAVING, and aggregates with FILTER.
- Handle NULL: `count(column)` vs `count(*)`, `coalesce`.
- Avoid join fan-out by aggregating before joining.

# 2 · Build: API contract

## Endpoint

| Method | Path                                                                   | Purpose                                                               |
|--------|------------------------------------------------------------------------|-----------------------------------------------------------------------|
| `GET`  | `/reports/doctor-load?from=YYYY-MM-DD&to=YYYY-MM-DD&minAppointments=0` | Load per active doctor, busiest first. `minAppointments` is optional. |

## Status codes

| Status | When                                                                                   |
|--------|----------------------------------------------------------------------------------------|
| 200    | A report, even if every count is zero                                                  |
| 400    | `to` before `from`, more than 92 days, a missing or malformed date, a negative minimum |

## Captured examples

Captured with curl from the running app on 15 Oct 2026, against the demo data. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: 5 to 11 October

**Why:** every active doctor, Dr Khan at zero, Dr Mehta at 3 with 3 follow-ups.

Request

``` code
GET /reports/doctor-load?from=2026-10-05&to=2026-10-11 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 596

{
  "from": "2026-10-05",
  "to": "2026-10-11",
  "doctors": [
    {
      "doctorId": 1,
      "name": "Dr Mehta",
      "speciality": "Cardiology",
      "appointments": 3,
      "completed": 2,
      "noShows": 1,
      "followUps": 3,
      "revenuePaise": 160000
    },
    {
      "doctorId": 2,
      "name": "Dr Iyer",
      "speciality": "Dermatology",
      "appointments": 2,
      "completed": 1,
      "noShows": 0,
      "followUps": 0,
      "revenuePaise": 60000
    },
    {
      "doctorId": 3,
      "name": "Dr Rao",
      "speciality": "Paediatrics",
      "appointments": 1,
      "completed": 1,
      "noShows": 0,
      "followUps": 0,
      "revenuePaise": 50000
    },
    {
      "doctorId": 4,
      "name": "Dr Khan",
      "speciality": "Orthopaedics",
      "appointments": 0,
      "completed": 0,
      "noShows": 0,
      "followUps": 0,
      "revenuePaise": 0
    }
  ]
}
```

### Case 2: `minAppointments=2`

**Why:** HAVING filters after counting.

Request

``` code
GET /reports/doctor-load?from=2026-10-05&to=2026-10-11&minAppointments=2 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 326

{
  "from": "2026-10-05",
  "to": "2026-10-11",
  "doctors": [
    {
      "doctorId": 1,
      "name": "Dr Mehta",
      "speciality": "Cardiology",
      "appointments": 3,
      "completed": 2,
      "noShows": 1,
      "followUps": 3,
      "revenuePaise": 160000
    },
    {
      "doctorId": 2,
      "name": "Dr Iyer",
      "speciality": "Dermatology",
      "appointments": 2,
      "completed": 1,
      "noShows": 0,
      "followUps": 0,
      "revenuePaise": 60000
    }
  ]
}
```

### Case 3: Sunday 11 October

**Why:** 23:30 on Sunday is in; 00:15 on Monday is not.

Request

``` code
GET /reports/doctor-load?from=2026-10-11&to=2026-10-11 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 583

{
  "from": "2026-10-11",
  "to": "2026-10-11",
  "doctors": [
    {
      "doctorId": 2,
      "name": "Dr Iyer",
      "speciality": "Dermatology",
      "appointments": 1,
      "completed": 0,
      "noShows": 0,
      "followUps": 0,
      "revenuePaise": 0
    },
    {
      "doctorId": 4,
      "name": "Dr Khan",
      "speciality": "Orthopaedics",
      "appointments": 0,
      "completed": 0,
      "noShows": 0,
      "followUps": 0,
      "revenuePaise": 0
    },
    {
      "doctorId": 1,
      "name": "Dr Mehta",
      "speciality": "Cardiology",
      "appointments": 0,
      "completed": 0,
      "noShows": 0,
      "followUps": 0,
      "revenuePaise": 0
    },
    {
      "doctorId": 3,
      "name": "Dr Rao",
      "speciality": "Paediatrics",
      "appointments": 0,
      "completed": 0,
      "noShows": 0,
      "followUps": 0,
      "revenuePaise": 0
    }
  ]
}
```

### Case 4: a week in January

**Why:** no appointments: everyone at 0, fees 0, not NULL.

Request

``` code
GET /reports/doctor-load?from=2026-01-05&to=2026-01-11 HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 583

{
  "from": "2026-01-05",
  "to": "2026-01-11",
  "doctors": [
    {
      "doctorId": 2,
      "name": "Dr Iyer",
      "speciality": "Dermatology",
      "appointments": 0,
      "completed": 0,
      "noShows": 0,
      "followUps": 0,
      "revenuePaise": 0
    },
    {
      "doctorId": 4,
      "name": "Dr Khan",
      "speciality": "Orthopaedics",
      "appointments": 0,
      "completed": 0,
      "noShows": 0,
      "followUps": 0,
      "revenuePaise": 0
    },
    {
      "doctorId": 1,
      "name": "Dr Mehta",
      "speciality": "Cardiology",
      "appointments": 0,
      "completed": 0,
      "noShows": 0,
      "followUps": 0,
      "revenuePaise": 0
    },
    {
      "doctorId": 3,
      "name": "Dr Rao",
      "speciality": "Paediatrics",
      "appointments": 0,
      "completed": 0,
      "noShows": 0,
      "followUps": 0,
      "revenuePaise": 0
    }
  ]
}
```

### Case 5: to before from

**Why:** `400`.

Request

``` code
GET /reports/doctor-load?from=2026-10-11&to=2026-10-05 HTTP/1.1
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "to is before from.",
  "instance": "/reports/doctor-load",
  "status": 400,
  "title": "Invalid date range"
}
```

## The old report, on the same data

The old SQL, run with psql against the same database after the captures (`docs/captures/old-report.txt`):

``` code
   name   | appointments 
----------+--------------
 Dr Mehta |            4
 Dr Iyer  |            2
 Dr Rao   |            1
(3 rows)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                   | What happens                      | Proved by                                           |
|--------------------------------------------------------|-----------------------------------|-----------------------------------------------------|
| A doctor with no appointments                          | Listed at 0                       | `theReportCountsEveryDoctorCorrectly`               |
| An appointment with two follow-ups                     | Counted once                      | `theWeekShowsEveryActiveDoctorBusiestFirst`         |
| Cancelled; retired doctor                              | Not counted; not listed           | `theWeekShowsEveryActiveDoctorBusiestFirst`         |
| 23:30 Sunday, 00:15 Monday                             | In; out                           | `theDaysAreIndiaDaysWithBothEndsIncluded`           |
| `minAppointments=2`                                    | Two doctors                       | `minAppointmentsFiltersAfterCounting`               |
| A week with nothing                                    | Everyone at 0                     | `aWeekWithNoAppointmentsListsEveryoneAtZero`        |
| Bad ranges                                             | `400`                             | `badRangesAre400`                                   |
| Unknown doctor, status, negative fee, orphan follow-up | Refused by named constraints      | `namedConstraintsHoldWithoutJava`                   |
| A failed import of appointments                        | Rolled back; the report unchanged | `aRolledBackDayOfAppointmentsNeverReachesTheReport` |

## The trap

Plausible but wrong

INNER JOIN hides doctors with zero appointments.

Four tests on the demo week. The old SQL leaves out Dr Khan and gives Dr Mehta 4. Switching to LEFT JOIN but keeping the date in WHERE leaves Dr Khan out again. Moving the date into ON but keeping `count(*)` gives Dr Khan an appointment he never had. The report gives 3, 2, 1 and 0. While building, each part of the query was undone once:

- An INNER JOIN turned 5 tests red.
- Conditions moved out of ON turned 5 red, and a date also in WHERE 5.
- `count(*)` turned 4 red.
- Follow-ups joined row by row turned 2 red.
- No `coalesce` turned 5 red (a NULL cannot become a number).
- Including retired doctors turned 3 red.

``` code
package com.mediqo.reports;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.Map;
import java.util.stream.Collectors;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.entry;

/** The first test written for this station: the old SQL against the demo week, then the two half-fixes. */
class InnerJoinTrapTest extends ApiTest {

    Map<String, Long> run(String sql) {
        OffsetDateTime from = LocalDate.parse(FROM).atStartOfDay(DoctorLoadReport.INDIA).toOffsetDateTime();
        OffsetDateTime to = LocalDate.parse(TO).plusDays(1).atStartOfDay(DoctorLoadReport.INDIA).toOffsetDateTime();
        return jdbc.sql(sql).param("from", from).param("to", to)
                .query((rs, n) -> Map.entry(rs.getString("name"), rs.getLong("appointments"))).list().stream()
                .collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue));
    }

    @Test
    void theOldReportHidesDrKhanAndCountsDrMehtasFollowUpsAsAppointments() {
        Map<String, Long> old = run(OldReportQueries.INNER_JOIN);
        assertThat(old).doesNotContainKey("Dr Khan");                // INNER JOIN: no appointments, no row
        assertThat(old).contains(entry("Dr Mehta", 4L));             // 3 appointments; the one with 2 follow-ups counted twice
    }

    @Test
    void aLeftJoinWithTheDateInWhereHidesHimAgain() {
        assertThat(run(OldReportQueries.LEFT_JOIN_FILTERED_IN_WHERE)).doesNotContainKey("Dr Khan");   // NULL >= date is not true
    }

    @Test
    void aLeftJoinWithCountStarGivesHimAnAppointmentHeNeverHad() {
        assertThat(run(OldReportQueries.LEFT_JOIN_COUNT_STAR)).contains(entry("Dr Khan", 1L));
    }

    @Test
    void theReportCountsEveryDoctorCorrectly() {
        Map<String, Long> now = report.between(LocalDate.parse(FROM), LocalDate.parse(TO), 0).stream()
                .collect(Collectors.toMap(DoctorLoadReport.Row::name, DoctorLoadReport.Row::appointments));
        assertThat(now).containsExactlyInAnyOrderEntriesOf(Map.of("Dr Mehta", 3L, "Dr Iyer", 2L, "Dr Rao", 1L, "Dr Khan", 0L));
    }
}
```

``` code
package com.mediqo.reports;

/** The report's SQL before the fix, kept only in tests: the first version, and two "fixes" that were not enough. */
final class OldReportQueries {

    private OldReportQueries() {
    }

    /** Version 1: INNER JOIN, follow-ups joined row by row, count(*). */
    static final String INNER_JOIN = """
            SELECT d.name, count(*) AS appointments
              FROM doctors d
              JOIN appointments a ON a.doctor_id = d.id
              LEFT JOIN follow_ups f ON f.appointment_id = a.id
             WHERE d.active AND a.starts_at >= :from AND a.starts_at < :to AND a.status <> 'CANCELLED'
             GROUP BY d.name""";

    /** "Fix" 1: LEFT JOIN, but the conditions on appointments are still in WHERE. */
    static final String LEFT_JOIN_FILTERED_IN_WHERE = """
            SELECT d.name, count(a.id) AS appointments
              FROM doctors d
              LEFT JOIN appointments a ON a.doctor_id = d.id
             WHERE d.active AND a.starts_at >= :from AND a.starts_at < :to AND a.status <> 'CANCELLED'
             GROUP BY d.name""";

    /** "Fix" 2: conditions moved to ON, but count(*) counts the empty row a LEFT JOIN makes for a doctor with none. */
    static final String LEFT_JOIN_COUNT_STAR = """
            SELECT d.name, count(*) AS appointments
              FROM doctors d
              LEFT JOIN appointments a ON a.doctor_id = d.id
                    AND a.starts_at >= :from AND a.starts_at < :to AND a.status <> 'CANCELLED'
             WHERE d.active
             GROUP BY d.name""";
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
./mvnw spring-boot:run      # the API on http://localhost:8080; Flyway loads the demo week
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

See a LEFT JOIN's empty row for yourself:

``` code
docker compose exec postgres psql -U mediqo -d mediqo -c "SELECT d.name, a.id AS appointment FROM doctors d LEFT JOIN appointments a ON a.doctor_id = d.id WHERE d.id = 4"
docker compose exec postgres psql -U mediqo -d mediqo -c "SELECT count(*), count(a.id) FROM doctors d LEFT JOIN appointments a ON a.doctor_id = d.id WHERE d.id = 4"
```

One row with an empty appointment; `count(*)` is 1, `count(a.id)` is 0.

## Troubleshooting

| You see                                     | Cause                                            | Fix                                                   |
|---------------------------------------------|--------------------------------------------------|-------------------------------------------------------|
| A doctor disappears from a LEFT JOIN report | A condition on the right table is in WHERE.      | Move it into the ON clause.                           |
| A doctor with nothing shows 1               | `count(*)` counts the empty row.                 | Count a column of the right table: `count(a.id)`.     |
| Totals are too high                         | A one-to-many join repeats rows before counting. | Aggregate the many side first, or count DISTINCT ids. |
| `null` instead of 0                         | `sum` of no rows is NULL.                        | `coalesce(sum(…), 0)`.                                |

## Project layout

``` tree
stations/041-clinic-appointments-report-with-joins/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/mediqo/reports/
│   ├── ReportController.java   ├── DoctorLoadReport.java   └── ReportsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__doctors_appointments_follow_ups.sql, V2__demo_week.sql
├── src/test/java/com/mediqo/reports/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels, then the database behind it.

#### `src/main/java/com/mediqo/reports/ReportController.java`

Does  
Reads and checks the date range, returns the report.

Why  
Range rules are checked before the database is asked.

Without it  
A year-long report that scans every appointment.

#### `src/main/java/com/mediqo/reports/DoctorLoadReport.java`

Does  
The report as one SQL query with `JdbcClient`.

Why  
LEFT JOIN with conditions in ON, follow-ups pre-counted, `count(a.id)`, `FILTER`, `coalesce`.

Without it  
The trap and its two half-fixes.

- `count(a.id) FILTER (WHERE …)` counts a subset in the same pass.
- The subquery turns follow-ups into one row per appointment before the join, so nothing repeats.
- Columns map to the record by name: `doctor_id` becomes `doctorId`.

#### `src/main/resources/db/migration/V1__doctors_appointments_follow_ups.sql`

Does  
Three tables, with named constraints and an index on doctor and time.

Why  
The index serves "this doctor's appointments in this range".

Without it  
A full scan of appointments for every doctor.

#### `src/main/resources/db/migration/V2__demo_week.sql`

The demo week, with every edge the tests need: a doctor with none, a retired doctor, follow-ups, a cancellation, and appointments at both ends of Sunday night.

#### `src/main/resources/application.yaml`

The database.

#### `compose.yaml`

PostgreSQL 17 for running the app.

#### `src/main/java/com/mediqo/reports/ReportsApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                   | Result |
|---------------|-------------------------------------------------------|------------------------------|--------|
| Every station | HTTP contract: valid, invalid, and an empty range     | `DoctorLoadContractTest` (5) | pass   |
| Every station | Reproduce the failure before the fix                  | `InnerJoinTrapTest` (4)      | pass   |
| Database      | Rollback and constraint tests against a real database | `ReportDatabaseTest` (2)     | pass   |

A report has nothing to be "not found": an empty range is a valid answer with every doctor at zero, and that is what the contract tests check.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.reports.InnerJoinTrapTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.reports.ReportDatabaseTest
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.reports.DoctorLoadContractTest
[INFO] Tests run: 11, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/mediqo/reports/InnerJoinTrapTest.java`

Written first: the old SQL and its two half-fixes, then the report.

#### `src/test/java/com/mediqo/reports/DoctorLoadContractTest.java`

The demo week, HAVING, the ends of a day, an empty week, and bad ranges.

#### `src/test/java/com/mediqo/reports/ReportDatabaseTest.java`

Named constraints, and a rolled-back import.

#### `src/test/java/com/mediqo/reports/OldReportQueries.java`

The old SQL, kept only in tests.

#### `src/test/java/com/mediqo/reports/ApiTest.java`

Shared setup and what the demo week contains.

#### `src/test/java/com/mediqo/reports/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/mediqo/reports/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=NoShowRateChallengeTest` (Docker must be running).
3.  Change the SQL until it passes, then run `./mvnw test` to check the other 11 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 13 tests pass (11 station tests and 2 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## No-show rate

Add `noShowPercent`: no-shows as a rounded whole percentage of appointments. A doctor with no appointments has no rate (`null`), not 0% and not an error.

**Done when:** the test in `NoShowRateChallengeTest` passes.

Hints

- `nullif(count(a.id), 0)` turns a zero divisor into NULL, and anything divided by NULL is NULL.
- Multiply by `100.0`, not `100`, or integer division drops the fraction first.

#### `challenge/NoShowRateChallengeTest.java`

``` code
package com.mediqo.reports;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.nullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 1: add "noShowPercent": no-shows as a whole-number percentage of appointments, rounded. A doctor with no
 * appointments has no rate at all (null), not 0% and not a division-by-zero error.
 */
class NoShowRateChallengeTest extends ApiTest {

    @Test
    void theRateIsRoundedAndMissingWhenThereIsNothingToDivide() throws Exception {
        mvc.perform(get("/reports/doctor-load").param("from", FROM).param("to", TO))
                .andExpect(jsonPath("$.doctors[*].name", contains("Dr Mehta", "Dr Iyer", "Dr Rao", "Dr Khan")))
                .andExpect(jsonPath("$.doctors[0].noShowPercent").value(33))
                .andExpect(jsonPath("$.doctors[1].noShowPercent").value(0))
                .andExpect(jsonPath("$.doctors[3].noShowPercent").value(nullValue()));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 25 minutes

## Load per speciality

Add `GET /reports/speciality-load?from&to`: per speciality, active doctors and appointments, busiest first, every speciality with an active doctor included.

**Done when:** the test in `SpecialityLoadChallengeTest` passes.

Hints

- After joining appointments, a doctor appears once per appointment: `count(DISTINCT d.id)`.
- Keep the LEFT JOIN and the conditions in ON, as in the main report.

#### `challenge/SpecialityLoadChallengeTest.java`

``` code
package com.mediqo.reports;

import org.junit.jupiter.api.Test;
import org.springframework.test.json.JsonCompareMode;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /reports/speciality-load?from&to: per speciality, how many active doctors and how many
 * appointments, busiest first, every speciality with an active doctor included. Counting doctors after joining
 * appointments repeats each doctor once per appointment: count each doctor once.
 */
class SpecialityLoadChallengeTest extends ApiTest {

    @Test
    void eachSpecialityCountsItsDoctorsOnce() throws Exception {
        mvc.perform(get("/reports/speciality-load").param("from", FROM).param("to", TO)).andExpect(status().isOk())
                .andExpect(content().json("""
                        [{"speciality":"Cardiology","doctors":1,"appointments":3},
                         {"speciality":"Dermatology","doctors":1,"appointments":2},
                         {"speciality":"Paediatrics","doctors":1,"appointments":1},
                         {"speciality":"Orthopaedics","doctors":1,"appointments":0}]""", JsonCompareMode.STRICT));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## A year, 200 clinics

Head office wants this report for any range up to a year, across 200 clinics with 3 crore appointments. Compare running the query on the main database, on a read replica, and from a daily summary table filled each night. What does each cost, how fresh is it, and how would you handle an appointment edited after its day was summarised?

# 3 · Go deeper: Design

## Implementation approach

1.  Write demo data with every edge: zero, retired, cancelled, follow-ups, both ends of a night.
2.  Write the trap test with the old SQL, then each half-fix.
3.  Write the report: LEFT JOIN, conditions in ON, pre-counted follow-ups, `count(a.id)`, `coalesce`.
4.  Check the whole response field by field.

## Design alternatives and trade-offs

| Approach                                                | What it costs                                                            | Verdict                |
|---------------------------------------------------------|--------------------------------------------------------------------------|------------------------|
| One SQL query with LEFT JOIN and FILTER                 | SQL to read carefully.                                                   | Chosen                 |
| INNER JOIN                                              | Zero-rows disappear.                                                     | The trap               |
| Joining follow-ups directly with `count(DISTINCT a.id)` | Correct counts, but sums over the joined rows (fees) would still repeat. | Fragile                |
| Load everything into Java and group there               | Moves every row over the network; fine for a week, not for a year.       | Small data only        |
| A JPA entity graph                                      | Many queries or huge joins for a summary.                                | Wrong tool for reports |

## Database design

| Table          | Key and constraints                                                                                                                  | Why                                                        |
|----------------|--------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------|
| `doctors`      | PK `id`; `active`                                                                                                                    | Retired doctors stay for history but leave reports.        |
| `appointments` | Identity PK. `appointments_doctor_fk`, `appointments_status_known`, `appointments_fee_not_negative`. Index `(doctor_id, starts_at)`. | The facts the report counts, with the index its join uses. |
| `follow_ups`   | Identity PK. `follow_ups_appointment_fk`.                                                                                            | One-to-many from appointments: the source of the fan-out.  |

``` code
CREATE TABLE doctors (
    id         BIGINT       PRIMARY KEY,
    name       VARCHAR(80)  NOT NULL,
    speciality VARCHAR(40)  NOT NULL,
    active     BOOLEAN      NOT NULL DEFAULT true
);

CREATE TABLE appointments (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    doctor_id    BIGINT      NOT NULL,
    patient_name VARCHAR(80) NOT NULL,
    starts_at    TIMESTAMPTZ NOT NULL,
    status       VARCHAR(10) NOT NULL,
    fee_paise    BIGINT      NOT NULL,
    CONSTRAINT appointments_doctor_fk    FOREIGN KEY (doctor_id) REFERENCES doctors (id),
    CONSTRAINT appointments_status_known CHECK (status IN ('BOOKED', 'COMPLETED', 'CANCELLED', 'NO_SHOW')),
    CONSTRAINT appointments_fee_not_negative CHECK (fee_paise >= 0)
);
CREATE INDEX appointments_doctor_time ON appointments (doctor_id, starts_at);

-- An appointment can lead to several follow-ups (a test next week, a review next month): one-to-many.
CREATE TABLE follow_ups (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    appointment_id BIGINT NOT NULL,
    due_on         DATE   NOT NULL,
    reason         VARCHAR(80) NOT NULL,
    CONSTRAINT follow_ups_appointment_fk FOREIGN KEY (appointment_id) REFERENCES appointments (id)
);
```

# 3 · Go deeper: Production

Report load  
Reports read many rows; run big ones on a read replica so they never slow down booking.

Check with EXPLAIN  
`EXPLAIN ANALYZE` shows whether the `(doctor_id, starts_at)` index is used. Check before the data grows, not after.

Time zones  
Store instants; turn India days into a time range once, in one place.

Reconciling  
A report that disagrees with the billing system is usually a join problem: compare row counts before and after each join.

# 3 · Go deeper: Interview

## Interview takeaways

INNER JOIN or LEFT JOIN?

INNER keeps only matching rows. LEFT keeps every row of the left table, with NULLs where nothing matches. Use LEFT when "none" is a valid answer you must show.

Why does a condition in WHERE break a LEFT JOIN?

WHERE runs after the join. For unmatched rows the right-side columns are NULL, and a comparison with NULL is not true, so WHERE removes exactly the rows the LEFT JOIN kept. Put such conditions in ON.

count(\*) or count(column)?

count(\*) counts rows, including the NULL row a LEFT JOIN creates; count(column) counts non-NULL values. To count matches, count a column of the right table.

What is join fan-out?

Joining a one-to-many relation repeats the 'one' row for each 'many'. Counts and sums over the 'one' side then grow. Aggregate the many side first, or count DISTINCT.

WHERE or HAVING?

WHERE filters rows before grouping; HAVING filters groups after aggregates are computed, such as 'at least 2 appointments'.

## Self-check rubric

| Area        | Meets the bar                    | Above the bar                                           |
|-------------|----------------------------------|---------------------------------------------------------|
| Correctness | All 11 tests pass.               | You predicted each half-fix's result before running it. |
| Joins       | LEFT JOIN with conditions in ON. | You can explain fan-out with a two-row example.         |
| NULL        | count(column), coalesce.         | NULLIF for safe division.                               |
| Data        | Demo data covering every edge.   | EXPLAIN shows the index in use.                         |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any report query:

- Can a group have zero rows? Does the join keep it?
- Is any condition on the right side of a LEFT JOIN in WHERE?
- Does a one-to-many join run before a count or a sum?
- Can any aggregate return NULL to the client?
