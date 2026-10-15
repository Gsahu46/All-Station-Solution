# Station 049 plan: Course enrolments with progress

**Problem.** Shikshalab mapped students and courses with @ManyToMany. When the business needed the enrolment date and
the lessons done per student and course, there was nowhere to put them: the mapping knows only the two ids.

**Endpoints.** `POST /courses/{id}/enrolments` {studentId} 201 + Location (404 course, 422 unknown student, 409 already
enrolled); `PATCH /enrolments/{id}/progress` {lessonsCompleted >= 0} 200 (422 beyond the course's lessons, 404);
`GET /students/{id}/courses` in enrolment order (404). Completed on = today (Asia/Kolkata) when every lesson is done;
cleared if progress goes back.

**Code.** Enrolment is an entity: two @ManyToOne (student, course) plus enrolledOn, lessonsCompleted, completedOn and
a copy of the course's lesson count. Clock bean for dates.

**Database.** enrolments_student_course_unique; enrolments_student_fk; enrolments_course_fk (course_id,
course_lessons) -> courses (id, lesson_count) ON UPDATE CASCADE; enrolments_progress_range;
enrolments_completed_when_done; courses_lesson_count_range.

**Tests.** ManyToManyTrapTest (test-only OldStudent @ManyToMany over the same table: adding fails on not-null; it sees
titles but not progress; removing one course from the List deletes all the student's rows and re-inserts ids only,
SQL saved in docs/bag-removal-sql.txt), EnrolmentContractTest, EnrolmentDatabaseTest (constraints, shrinking a
course below progress refused whole, 30 clicks -> one enrolment). Mutations: no completed date -> 1 red; no beyond
check -> 1 (500 instead of 422); no unique-violation catch -> red in 2 of 3 full runs (a race test can miss); no
exists check -> 0 (the constraint answers 409).

**Practice.** 1: unenrol (completed courses stay). 2: course roster from the other side. Design: when is a plain
@ManyToMany still fine.
