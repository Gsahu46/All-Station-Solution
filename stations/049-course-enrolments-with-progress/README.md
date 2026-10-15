# Station 049 · Course enrolments with progress

Foundations · 0–1 years · Core · Edtech · Types: Database

Spring Boot 4.1.1 · Java 25 · Spring Data JPA (Hibernate 7) · join entity with two @ManyToOne · composite unique and foreign keys · PostgreSQL 17 · Flyway · Testcontainers. Needs JDK 25 (or 21, see Set up & code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Students, courses and progress are demo data, not Shikshalab's. Progress is a number the client reports; no video player or quiz is involved. The student is named in the request body because this station has no login.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 13 tests.

# 1 · Understand

## The problem in real life

1.  **A list of courses**

    Shikshalab's students had a list of courses, mapped with `@ManyToMany`. Simple, and fine while a link was just a link.

2.  **Then the link needed data**

    The business wanted the enrolment date and how many lessons each student had done in each course. The mapping had no place for either: it writes the two ids and nothing else.

3.  **The fix**

    Make the link an entity, `Enrolment`, with its own id, date and progress, two `@ManyToOne`s, and the pair unique in the database.

When a link between two things has facts of its own, the link is a thing too.

## What are we building?

A student enrols in a course (`POST /courses/{id}/enrolments`), reports lessons done (`PATCH /enrolments/{id}/progress`), and sees their courses with progress (`GET /students/{id}/courses`). Each student–course pair is one row with its own date and progress.

## An everyday analogy

An airline could keep "Asha flies to Delhi" as a line in a list. Once it needs her seat and boarding time, it prints a boarding pass: a document for that one passenger on that one flight. `Enrolment` is the boarding pass.

## How it works in 4 steps

1.  **Enrolling** inserts one `enrolments` row: student, course, today's date, 0 lessons.
2.  **The pair is unique**, so a second enrolment of the same student in the same course is refused.
3.  **Progress** updates that row; the database checks it against the course's lesson count.
4.  **Listing** a student's courses reads their rows, with each course joined in.

Check yourself: why not add a `progress` column to `courses`?

A course row is shared by every student in it. Progress belongs to one student in one course, so it can only live on the row for that pair.

## What this station is not

- **No login.** The student is named in the body.
- **No lessons table.** Progress is a count, not which lessons.
- **No unenrolling.** That is challenge 1.

## Key terms

| Term                            | Simple meaning                                                         | Everyday example                                             | In this project                    |
|---------------------------------|------------------------------------------------------------------------|--------------------------------------------------------------|------------------------------------|
| **Many-to-many**                | Each student takes many courses; each course has many students.        | Passengers and flights.                                      | Students and courses               |
| **Join table**                  | A table with one row per pair, holding both ids.                       | The boarding list: passenger, flight.                        | `enrolments`                       |
| **Join entity**                 | That table as a Java class of its own, with its own fields.            | A boarding pass: passenger, flight, seat, boarding time.     | `Enrolment`                        |
| **`@ManyToMany`**               | A mapping that hides the join table: a list of courses on the student. | A list of flights in the passenger's head, no boarding pass. | `OldStudent` (tests only)          |
| **Composite unique constraint** | Two columns together may not repeat.                                   | One boarding pass per passenger per flight.                  | `enrolments_student_course_unique` |
| **Composite foreign key**       | Two columns that must match two columns of another table's row.        | The seat count printed on the pass must match the plane's.   | `enrolments_course_fk`             |

# 2 · Build: Spec

## Business problem

**Shikshalab** (a fictional edtech platform) needs, for every student in every course, when they enrolled and how far they got. The old `@ManyToMany` mapping cannot hold either.

## Acceptance criteria

1.  **Given** Asha enrols in Spring Boot from zero, **then** `201`, today's date (India), 0 of 40 lessons.
2.  **Given** she reports 12 lessons, **then** 30%, and Rahul in the same course still has 0.
3.  **Given** she finishes all 8 lessons of Git basics, **then** 100% and a completion date; reporting 7 again clears it.
4.  **Given** she enrols twice, or 30 clicks arrive at once, **then** one enrolment; the others are `409`.
5.  **Given** 41 lessons of 40, **then** `422`; −1, missing or not a number, `400`; an unknown student in the body, `422`.
6.  **Given** an unknown course, enrolment or student in the path, **then** `404`.

## Requirements

- One enrolment per student per course, enforced by a composite unique constraint.
- Progress between 0 and the course's lessons, enforced by the database too.
- A completion date exactly when every lesson is done, enforced by the database too.
- Dates are Indian dates (`Asia/Kolkata`).

## Learning objectives

- Replace `@ManyToMany` with a join entity and two `@ManyToOne`s.
- Put rules about a pair in the database: composite unique and composite foreign keys.
- Explain why `@ManyToMany` fails for links with data, and what Hibernate does when one element is removed from a list.
- Read a many-to-many from either side through the join entity.

# 2 · Build: API contract

## Endpoints

| Method  | Path                        | Purpose                                                                     |
|---------|-----------------------------|-----------------------------------------------------------------------------|
| `POST`  | `/courses/{id}/enrolments`  | Enrol a student: `{"studentId": 1}`.                                        |
| `PATCH` | `/enrolments/{id}/progress` | Report lessons done: `{"lessonsCompleted": 12}` (a total, not an increase). |
| `GET`   | `/students/{id}/courses`    | The student's enrolments with course, progress and dates, oldest first.     |

## Status codes

| Status | When                                                          |
|--------|---------------------------------------------------------------|
| 201    | Enrolled; `Location` points at the enrolment                  |
| 200    | Progress recorded; or the list                                |
| 400    | Student missing; lessons missing, negative or not a number    |
| 404    | No such course, enrolment or student in the path              |
| 409    | Already enrolled in this course                               |
| 422    | Unknown student in the body; more lessons than the course has |

## Captured examples

Captured with curl from the running app on 15 Oct 2026, in this order, against one fresh database. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: Asha enrols in Spring Boot from zero

**Why:** a new pair: today, 0 of 40.

Request

``` code
POST /courses/1/enrolments HTTP/1.1
Content-Type: application/json

{
  "studentId": 1
}
```

Response

``` code
HTTP/1.1 201 
Location: /enrolments/1
Content-Type: application/json

{
  "id": 1,
  "studentId": 1,
  "courseId": 1,
  "courseTitle": "Spring Boot from zero",
  "enrolledOn": "2026-10-15",
  "lessonsCompleted": 0,
  "lessonCount": 40,
  "progressPercent": 0,
  "completedOn": null
}
```

### Case 2: and in Git basics

**Why:** a second row for the same student.

Request

``` code
POST /courses/3/enrolments HTTP/1.1
Content-Type: application/json

{
  "studentId": 1
}
```

Response

``` code
HTTP/1.1 201 
Location: /enrolments/2
Content-Type: application/json

{
  "id": 2,
  "studentId": 1,
  "courseId": 3,
  "courseTitle": "Git basics",
  "enrolledOn": "2026-10-15",
  "lessonsCompleted": 0,
  "lessonCount": 8,
  "progressPercent": 0,
  "completedOn": null
}
```

### Case 3: Rahul enrols in Spring Boot

**Why:** a second row for the same course.

Request

``` code
POST /courses/1/enrolments HTTP/1.1
Content-Type: application/json

{
  "studentId": 2
}
```

Response

``` code
HTTP/1.1 201 
Location: /enrolments/3
Content-Type: application/json

{
  "id": 3,
  "studentId": 2,
  "courseId": 1,
  "courseTitle": "Spring Boot from zero",
  "enrolledOn": "2026-10-15",
  "lessonsCompleted": 0,
  "lessonCount": 40,
  "progressPercent": 0,
  "completedOn": null
}
```

### Case 4: Asha has done 12 lessons

**Why:** her row only: 30%.

Request

``` code
PATCH /enrolments/1/progress HTTP/1.1
Content-Type: application/json

{
  "lessonsCompleted": 12
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 178

{
  "id": 1,
  "studentId": 1,
  "courseId": 1,
  "courseTitle": "Spring Boot from zero",
  "enrolledOn": "2026-10-15",
  "lessonsCompleted": 12,
  "lessonCount": 40,
  "progressPercent": 30,
  "completedOn": null
}
```

### Case 5: Asha finishes Git basics

**Why:** 8 of 8: completed today.

Request

``` code
PATCH /enrolments/2/progress HTTP/1.1
Content-Type: application/json

{
  "lessonsCompleted": 8
}
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 174

{
  "id": 2,
  "studentId": 1,
  "courseId": 3,
  "courseTitle": "Git basics",
  "enrolledOn": "2026-10-15",
  "lessonsCompleted": 8,
  "lessonCount": 8,
  "progressPercent": 100,
  "completedOn": "2026-10-15"
}
```

### Case 6: Asha's courses

**Why:** each with its own date and progress.

Request

``` code
GET /students/1/courses HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 355

[
  {
    "id": 1,
    "studentId": 1,
    "courseId": 1,
    "courseTitle": "Spring Boot from zero",
    "enrolledOn": "2026-10-15",
    "lessonsCompleted": 12,
    "lessonCount": 40,
    "progressPercent": 30,
    "completedOn": null
  },
  {
    "id": 2,
    "studentId": 1,
    "courseId": 3,
    "courseTitle": "Git basics",
    "enrolledOn": "2026-10-15",
    "lessonsCompleted": 8,
    "lessonCount": 8,
    "progressPercent": 100,
    "completedOn": "2026-10-15"
  }
]
```

### Case 7: Asha enrols in Spring Boot again

**Why:** the pair exists: `409`.

Request

``` code
POST /courses/1/enrolments HTTP/1.1
Content-Type: application/json

{
  "studentId": 1
}
```

Response

``` code
HTTP/1.1 409 
Content-Type: application/problem+json

{
  "detail": "Student 1 is already enrolled in course 1.",
  "instance": "/courses/1/enrolments",
  "status": 409,
  "title": "Already enrolled"
}
```

### Case 8: 41 lessons of 40

**Why:** `422`.

Request

``` code
PATCH /enrolments/1/progress HTTP/1.1
Content-Type: application/json

{
  "lessonsCompleted": 41
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "\"Spring Boot from zero\" has 40 lessons; 41 cannot be completed.",
  "instance": "/enrolments/1/progress",
  "status": 422,
  "title": "Beyond the course"
}
```

### Case 9: student 99

**Why:** `404`.

Request

``` code
GET /students/99/courses HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No student 99.",
  "instance": "/students/99/courses",
  "status": 404,
  "title": "Student not found"
}
```

## The join table

Read with psql after the requests above (`docs/captures/rows.txt`).

``` code
 id | student_id | course_id | course_lessons | enrolled_on | lessons_completed | completed_on 
----+------------+-----------+----------------+-------------+-------------------+--------------
  1 |          1 |         1 |             40 | 2026-10-15  |                12 | 
  2 |          1 |         3 |              8 | 2026-10-15  |                 8 | 2026-10-15
  3 |          2 |         1 |             40 | 2026-10-15  |                 0 | 
(3 rows)
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                                                         | What happens                                               | Proved by                                             |
|----------------------------------------------------------------------------------------------|------------------------------------------------------------|-------------------------------------------------------|
| A new enrolment                                                                              | Today, 0 lessons, `Location`                               | `anEnrolmentStartsTodayAtZero`                        |
| Two students in one course                                                                   | Each has their own progress                                | `progressIsKeptPerStudentAndCourse`                   |
| The last lesson, then one undone                                                             | Completion date set, then cleared                          | `theLastLessonCompletesTheCourseAndUndoingItReopens`  |
| A student's courses                                                                          | In enrolment order                                         | `aStudentsCoursesComeInEnrolmentOrder`                |
| Enrol twice                                                                                  | `409`                                                      | `enrollingTwiceIs409`                                 |
| Bad bodies; too many lessons; unknown student                                                | `400`; `422`; `422`                                        | `badRequestsAre400Or422`                              |
| Unknown course, enrolment, student                                                           | `404`                                                      | `unknownCoursesEnrolmentsAndStudentsAre404`           |
| Duplicates, wrong lesson count, progress out of range, completion mismatch, written directly | Refused by named constraints                               | `namedConstraintsHoldWithoutJava`                     |
| A course shrunk below someone's progress                                                     | Refused, nothing changes; growing it follows into the rows | `shrinkingACourseBelowSomeonesProgressIsRefusedWhole` |
| 30 clicks on Enrol at once                                                                   | One `201`, 29 `409`                                        | `thirtyClicksOnEnrolMakeOneEnrolment`                 |

## The trap

Plausible but wrong

`@ManyToMany` for a link that needs its own data, with nowhere to store it.

The old mapping is kept in the tests as `OldStudent`: a `List<Course>` over the same `enrolments` table. Three tests show what it cannot do. Adding a course fails, because it writes only the two ids and the table needs a date and a lesson count. Reading works but sees titles only: Asha's 12 of 40 lessons are in the row and nowhere in the model. Removing one course is worse: for a list, Hibernate deletes all of the student's rows and re-inserts the ones left, with ids only. The SQL, from a run of that test (`docs/bag-removal-sql.txt`):

``` code
# ManyToManyTrapTest#droppingOneCourseRewritesTheWholeList, run with -Dspring.jpa.show-sql=true on 15 Oct 2026
Hibernate: insert into enrolments (completed_on,course_id,course_lessons,enrolled_on,lessons_completed,student_id) values (?,?,?,?,?,?)
Hibernate: insert into enrolments (completed_on,course_id,course_lessons,enrolled_on,lessons_completed,student_id) values (?,?,?,?,?,?)
Hibernate: delete from enrolments where student_id=?
Hibernate: insert into enrolments (student_id,course_id) values (?,?)
PostgreSQL: ERROR: null value in column "course_lessons" of relation "enrolments" violates not-null constraint
```

Here the re-insert fails and the transaction rolls back. On a join table with defaults instead of `NOT NULL`, it would have succeeded and silently reset every other course's date and progress.

While building, each part was undone once. Without setting the completion date, 1 test turned red; without the "beyond the course" check, 1 (the database refused it, as a `500` instead of a `422`). Without turning the unique violation into `409`, the 30-click test turned red in 2 of 3 full runs: a race test can miss, because the check before the insert answers most clicks. Removing that check turned nothing red: the constraint answers `409` on its own.

``` code
package com.shikshalab.learning;

import jakarta.persistence.EntityManager;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: the old @ManyToMany, on the table the business now needs. It can only
 * write the two ids, and it treats the link as a list of courses, not as rows with data of their own.
 */
class ManyToManyTrapTest extends ApiTest {

    @Autowired
    EntityManager entities;
    @Autowired
    TransactionTemplate transaction;

    @Test
    void manyToManyCannotWriteTheDateOrTheProgress() {
        // Asha enrols in Git basics the old way: add the course to her list.
        assertThatThrownBy(() -> transaction.executeWithoutResult(status ->
                entities.find(OldStudent.class, 1L).courses.add(entities.find(Course.class, 3L))))
                .hasMessageContaining("violates not-null constraint");   // course_lessons, enrolled_on: the mapping has no value for them
        assertThat(jdbc.sql("SELECT count(*) FROM enrolments").query(Long.class).single()).isZero();
    }

    @Test
    void itSeesTheCoursesButNotHowFarSheGot() throws Exception {
        enrol(1, 1).andExpect(status().isCreated());
        progress(1, "{\"lessonsCompleted\":12}").andExpect(status().isOk());
        List<String> titles = transaction.execute(status -> entities.find(OldStudent.class, 1L).courses.stream().map(Course::getTitle).toList());
        assertThat(titles).containsExactly("Spring Boot from zero");   // and nothing else: 12 of 40 lessons is in the row, not in the model
        assertThat(jdbc.sql("SELECT lessons_completed FROM enrolments WHERE student_id = 1").query(Integer.class).single()).isEqualTo(12);
    }

    @Test
    void droppingOneCourseRewritesTheWholeList() throws Exception {
        enrol(1, 1);
        enrol(2, 1);
        progress(2, "{\"lessonsCompleted\":10}");
        // With a List (a "bag"), Hibernate cannot delete one row: it deletes all of Asha's rows and re-inserts the rest.
        // The re-insert has no date, lesson count or progress, so it fails, and she cannot drop a course at all.
        assertThatThrownBy(() -> transaction.executeWithoutResult(status ->
                entities.find(OldStudent.class, 1L).courses.removeIf(c -> c.getId() == 1L)))
                .hasMessageContaining("violates not-null constraint");
        assertThat(jdbc.sql("SELECT lessons_completed FROM enrolments WHERE course_id = 2").query(Integer.class).single()).isEqualTo(10);
    }
}
```

``` code
package com.shikshalab.learning;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.JoinTable;
import jakarta.persistence.ManyToMany;
import jakarta.persistence.Table;

import java.util.ArrayList;
import java.util.List;

/**
 * The mapping as it shipped, kept only in tests: a plain @ManyToMany over the same join table. It knows the two ids
 * and nothing else, so there is no field for the date or the progress, and nowhere to put one.
 */
@Entity
@Table(name = "students")
public class OldStudent {

    @Id
    Long id;
    String name;
    @ManyToMany
    @JoinTable(name = "enrolments", joinColumns = @JoinColumn(name = "student_id"), inverseJoinColumns = @JoinColumn(name = "course_id"))
    List<Course> courses = new ArrayList<>();
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
./mvnw test                 # all 13 tests; starts its own PostgreSQL container
```

**Windows (PowerShell)**

``` code
docker compose up -d
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

See the SQL behind the trap for yourself:

``` code
./mvnw test -Dtest=ManyToManyTrapTest#droppingOneCourseRewritesTheWholeList -Dspring.jpa.show-sql=true
```

Look for `delete from enrolments where student_id=?` followed by an insert of two columns. Then change `List<Course>` to `Set<Course>` in `OldStudent` and run it again: Hibernate can now delete the one row, and that test fails because nothing breaks (`delete from enrolments where student_id=? and course_id=?` was checked the same way). A set fixes the rewrite, not the missing date and progress.

## Troubleshooting

| You see                                                                 | Cause                                                  | Fix                                            |
|-------------------------------------------------------------------------|--------------------------------------------------------|------------------------------------------------|
| `null value in column ... violates not-null constraint` on a join table | A `@ManyToMany` writing a table that has more columns. | Map the join table as an entity.               |
| `delete from ... where student_id=?` when removing one element          | A `@ManyToMany` list (bag): Hibernate rewrites it.     | A join entity; or at least a `Set`.            |
| `500` on a double click                                                 | The unique violation is not mapped.                    | Catch it by constraint name and answer `409`.  |
| `enrolments_course_fk` when inserting directly                          | `course_lessons` does not match the course.            | Copy the course's lesson count when enrolling. |
| Yesterday's date just after midnight                                    | Dates taken in UTC.                                    | A `Clock` in `Asia/Kolkata`.                   |

## Project layout

``` tree
stations/049-course-enrolments-with-progress/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/shikshalab/learning/
│   ├── EnrolmentController.java   ├── EnrolmentDesk.java   ├── Enrolment.java   ├── Repositories.java
│   ├── Student.java   ├── Course.java   └── LearningApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__students_courses_enrolments.sql, V2__demo_school.sql
├── src/test/java/com/shikshalab/learning/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs, the old mapping's SQL
```

## Code walkthrough

In the order a request travels, then the entities and the database.

#### `src/main/java/com/shikshalab/learning/EnrolmentController.java`

Does  
Validates the bodies; `Location` on enrol.

Why  
HTTP only.

Without it  
Progress below zero reaching the service.

#### `src/main/java/com/shikshalab/learning/EnrolmentDesk.java`

Does  
Enrols, records progress, lists a student's courses.

Why  
The pair check is a fast path; the unique constraint is the guarantee, mapped to `409`.

Without it  
Two enrolments from a double click.

#### `src/main/java/com/shikshalab/learning/Enrolment.java`

Does  
The join entity: student, course, date, progress, completion.

Why  
Two `@ManyToOne`s replace the `@ManyToMany`; the link has fields of its own.

Without it  
Progress with nowhere to live.

- `courseLessons` copies the course's lesson count so the database can check progress against it.
- `recordProgress` sets or clears the completion date with the count.

#### `src/main/java/com/shikshalab/learning/Repositories.java`

Student, course and enrolment repositories; the enrolment queries join the course in.

#### `src/main/java/com/shikshalab/learning/Student.java`

A student. No list of courses: the courses are read through enrolments.

#### `src/main/java/com/shikshalab/learning/Course.java`

A course and its lesson count.

#### `src/main/resources/db/migration/V1__students_courses_enrolments.sql`

The tables and named constraints, including the composite foreign key to the course's lesson count.

#### `src/main/resources/db/migration/V2__demo_school.sql`

Two students, three courses.

#### `src/main/java/com/shikshalab/learning/LearningApplication.java`

Entry point; a `Clock` in India time for dates.

#### `src/main/resources/application.yaml`

open-in-view off; schema validation; decimals refused for whole-number fields.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                           | Test class                  | Result |
|---------------|-------------------------------------------------------|-----------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found              | `EnrolmentContractTest` (7) | pass   |
| Every station | Reproduce the failure before the fix                  | `ManyToManyTrapTest` (3)    | pass   |
| Database      | Rollback and constraint tests against a real database | `EnrolmentDatabaseTest` (3) | pass   |

## Run output

JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.shikshalab.learning.ManyToManyTrapTest
[INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0 -- in com.shikshalab.learning.EnrolmentDatabaseTest
[INFO] Tests run: 7, Failures: 0, Errors: 0, Skipped: 0 -- in com.shikshalab.learning.EnrolmentContractTest
[INFO] Tests run: 13, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/shikshalab/learning/ManyToManyTrapTest.java`

Written first: what the old `@ManyToMany` cannot write, cannot show, and does on removal.

#### `src/test/java/com/shikshalab/learning/EnrolmentContractTest.java`

Enrol, progress, list, and every refusal.

#### `src/test/java/com/shikshalab/learning/EnrolmentDatabaseTest.java`

Named constraints, a refused course change, and 30 clicks at once (virtual threads and a start latch).

#### `src/test/java/com/shikshalab/learning/OldStudent.java`

The old mapping, kept only in tests.

#### `src/test/java/com/shikshalab/learning/ApiTest.java`

Shared setup: no enrolments before each test; today's date in India.

#### `src/test/java/com/shikshalab/learning/PostgresTestConfig.java`

PostgreSQL 17 in Docker via Testcontainers.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/shikshalab/learning/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=UnenrolChallengeTest` (Docker must be running).
3.  Change the code until it passes, then run `./mvnw test` to check the other 13 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 16 tests pass (13 station tests and 3 challenge tests).

Challenge 1 · Beginner-friendly · about 20 minutes

## Drop a course

Add `DELETE /enrolments/{id}`: `204`, and the course leaves the student's list while the others keep their progress. A completed course stays (`409`); unknown is `404`.

**Done when:** both tests in `UnenrolChallengeTest` pass.

Hints

- Deleting one `Enrolment` deletes one row: compare with the trap's rewrite.
- Check `completedOn` before deleting.

#### `challenge/UnenrolChallengeTest.java`

``` code
package com.shikshalab.learning;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: DELETE /enrolments/{id} drops a course: 204, and it leaves the student's list while their other
 * courses keep their progress. A completed course is part of the record and cannot be dropped (409). Unknown: 404.
 */
class UnenrolChallengeTest extends ApiTest {

    @Test
    void droppingOneCourseLeavesTheOthersAlone() throws Exception {
        enrol(1, 1);
        enrol(2, 1);
        progress(2, "{\"lessonsCompleted\":10}");
        mvc.perform(delete("/enrolments/1")).andExpect(status().isNoContent());
        mvc.perform(get("/students/1/courses")).andExpect(jsonPath("$.length()").value(1))
                .andExpect(jsonPath("$[0].courseId").value(2)).andExpect(jsonPath("$[0].lessonsCompleted").value(10));
        enrol(1, 1).andExpect(status().isCreated());   // and she can enrol again later, from zero
    }

    @Test
    void completedOrUnknownEnrolmentsStay() throws Exception {
        enrol(3, 1);
        progress(1, "{\"lessonsCompleted\":8}");
        mvc.perform(delete("/enrolments/1")).andExpect(status().isConflict());
        mvc.perform(delete("/enrolments/99")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 25 minutes

## A course roster

Add `GET /courses/{id}/students`: the students in a course with their progress, furthest along first, then by name.

**Done when:** the test in `CourseRosterChallengeTest` passes.

Hints

- A derived query on the join entity: `findByCourseIdOrderByLessonsCompletedDescStudentNameAsc`.
- Join the student in with an entity graph, so the roster is one query.

#### `challenge/CourseRosterChallengeTest.java`

``` code
package com.shikshalab.learning;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /courses/{id}/students lists who is enrolled, from the other side of the link: studentId, name,
 * lessonsCompleted, progressPercent, completedOn, furthest along first, then by name. Unknown course: 404.
 */
class CourseRosterChallengeTest extends ApiTest {

    @Test
    void theRosterIsReadThroughTheJoinEntity() throws Exception {
        enrol(2, 1);
        enrol(2, 2);
        progress(2, "{\"lessonsCompleted\":24}");
        progress(1, "{\"lessonsCompleted\":6}");
        mvc.perform(get("/courses/2/students")).andExpect(status().isOk()).andExpect(content().json("""
                [{"studentId":2,"name":"Rahul Menon","lessonsCompleted":24,"progressPercent":100,"completedOn":"%s"},
                 {"studentId":1,"name":"Asha Verma","lessonsCompleted":6,"progressPercent":25,"completedOn":null}]""".formatted(today()), true));
        mvc.perform(get("/courses/3/students")).andExpect(content().json("[]"));
        mvc.perform(get("/courses/99/students")).andExpect(status().isNotFound());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## When is `@ManyToMany` still fine?

List three many-to-many links in apps you know (tags on posts, roles of users, products in categories, …). For each, decide whether the link will ever need its own data, how you would find out, and what migrating from `@ManyToMany` to a join entity would cost later.

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap tests with the old mapping on the new table.
2.  Design the join table first: its own id, the pair, its own columns, and the rules on them.
3.  Map it as an entity with two `@ManyToOne`s; drop the collections from `Student` and `Course`.
4.  Query from either side through the join entity.

## Design alternatives and trade-offs

| Approach                                                   | What it costs                                                    | Verdict  |
|------------------------------------------------------------|------------------------------------------------------------------|----------|
| Join entity with its own id                                | One more class; the pair needs a unique constraint.              | Chosen   |
| `@ManyToMany`                                              | No room for link data; a list rewrites the table on removal.     | The trap |
| Join entity with a composite id (`@EmbeddedId`, `@MapsId`) | No extra id column; more mapping code, ids of two parts in URLs. | Valid    |
| Progress in a separate table keyed by student and course   | Two tables describing one link, kept in step by hand.            | No       |
| A JSON column of progress on the student                   | No constraints, no joins, no per-course queries.                 | No       |

## Database design

| Table        | Constraints                                                                                                                                                                      | Mapped as                                    |
|--------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------|
| `enrolments` | `enrolments_student_course_unique`, `enrolments_student_fk`, `enrolments_course_fk` (course and its lesson count), `enrolments_progress_range`, `enrolments_completed_when_done` | `Enrolment`: `@ManyToOne` student and course |
| `courses`    | `courses_lesson_count_range`, `courses_id_lessons_unique`                                                                                                                        | `Course`                                     |
| `students`   | Primary key                                                                                                                                                                      | `Student`                                    |

``` code
-- Shikshalab: students and courses are many-to-many; each pair (an enrolment) has its own date and progress.
CREATE TABLE students (
    id   BIGINT PRIMARY KEY,
    name VARCHAR(80) NOT NULL
);

CREATE TABLE courses (
    id           BIGINT PRIMARY KEY,
    title        VARCHAR(120) NOT NULL,
    lesson_count INT          NOT NULL,
    CONSTRAINT courses_lesson_count_range CHECK (lesson_count BETWEEN 1 AND 500),
    CONSTRAINT courses_id_lessons_unique UNIQUE (id, lesson_count)   -- target of enrolments_course_fk
);

-- The join table, with columns of its own. The pair is unique; progress is checked against the course's lessons.
CREATE TABLE enrolments (
    id                BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    student_id        BIGINT NOT NULL,
    course_id         BIGINT NOT NULL,
    course_lessons    INT    NOT NULL,
    enrolled_on       DATE   NOT NULL,
    lessons_completed INT    NOT NULL DEFAULT 0,
    completed_on      DATE,
    CONSTRAINT enrolments_student_fk FOREIGN KEY (student_id) REFERENCES students (id),
    -- course_lessons must be the course's real lesson count; ON UPDATE CASCADE follows a change to the course.
    CONSTRAINT enrolments_course_fk FOREIGN KEY (course_id, course_lessons) REFERENCES courses (id, lesson_count) ON UPDATE CASCADE,
    CONSTRAINT enrolments_student_course_unique UNIQUE (student_id, course_id),
    CONSTRAINT enrolments_progress_range CHECK (lessons_completed BETWEEN 0 AND course_lessons),
    CONSTRAINT enrolments_completed_when_done CHECK ((lessons_completed = course_lessons) = (completed_on IS NOT NULL))
);

CREATE INDEX enrolments_course ON enrolments (course_id);
```

# 3 · Go deeper: Production

Migrating from `@ManyToMany`  
Add the id and new columns to the existing join table in a migration, with values for old rows (an enrolment date you can defend, such as the first activity), then switch the mapping. The rows stay; their meaning grows.

Indexes on both sides  
The unique constraint indexes (student, course), which serves "a student's courses". "A course's students" needs its own index on `course_id`.

Changing a course  
The composite foreign key follows a new lesson count into every enrolment, and refuses one that would leave someone past the end. Decide with the content team what happens to those students first.

Progress from clients  
A client reports a total, not "+1", so a retried request cannot count a lesson twice.

# 3 · Go deeper: Interview

## Interview takeaways

When do you replace @ManyToMany with a join entity?

As soon as the link has data of its own (a date, a role, a quantity, a status) or will be queried on its own. In practice, most business links end up there.

What does Hibernate do when you remove one element from a @ManyToMany List?

For a bag (List without an order column), it deletes every row for the owner and re-inserts the remaining ones. A Set lets it delete just the one row.

How do you stop the same student enrolling twice?

A unique constraint on (student_id, course_id). A check in code first is a nicety; the constraint holds under concurrent requests, and its violation becomes 409.

How can the database check progress against the course's lesson count?

Copy the lesson count into the enrolment and tie it with a composite foreign key to (id, lesson_count) on courses, ON UPDATE CASCADE; then a CHECK compares the two columns of the same row.

Surrogate id or composite id for the join entity?

A surrogate id is simpler to map and to put in URLs; a composite id avoids a column. Either way, the pair needs a unique constraint.

## Self-check rubric

| Area        | Meets the bar                                  | Above the bar                                 |
|-------------|------------------------------------------------|-----------------------------------------------|
| Correctness | All 13 tests pass.                             | You saw the delete-all SQL yourself.          |
| Mapping     | A join entity with two `@ManyToOne`s.          | You can say when `@ManyToMany` is still fine. |
| Integrity   | Unique pair; progress checked by the database. | You can explain the composite foreign key.    |
| Queries     | A student's courses in one query.              | The roster from the other side.               |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any many-to-many:

- Does the link have, or will it soon have, data of its own?
- Is the pair unique in the database, not just in code?
- If `@ManyToMany` stays, is it a `Set`, and what SQL runs when one element is removed?
- Can both sides be queried without loading whole collections?
