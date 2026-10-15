"""Station 049 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 49,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring Data JPA (Hibernate 7) · join entity with two @ManyToOne · composite unique and foreign keys · PostgreSQL 17 · Flyway · Testcontainers",
    "simulation": "Students, courses and progress are demo data, not Shikshalab's. Progress is a number the client reports; no video player or quiz is involved. The student is named in the request body because this station has no login.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/shikshalab/learning/"
T = "src/test/java/com/shikshalab/learning/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Many-to-many", "Each student takes many courses; each course has many students.", "Passengers and flights.", "Students and courses"),
    ("Join table", "A table with one row per pair, holding both ids.", "The boarding list: passenger, flight.", "<code>enrolments</code>"),
    ("Join entity", "That table as a Java class of its own, with its own fields.", "A boarding pass: passenger, flight, seat, boarding time.", "<code>Enrolment</code>"),
    ("<code>@ManyToMany</code>", "A mapping that hides the join table: a list of courses on the student.", "A list of flights in the passenger's head, no boarding pass.", "<code>OldStudent</code> (tests only)"),
    ("Composite unique constraint", "Two columns together may not repeat.", "One boarding pass per passenger per flight.", "<code>enrolments_student_course_unique</code>"),
    ("Composite foreign key", "Two columns that must match two columns of another table's row.", "The seat count printed on the pass must match the plane's.", "<code>enrolments_course_fk</code>"),
]
STORY = [
    ("A list of courses", "Shikshalab's students had a list of courses, mapped with <code>@ManyToMany</code>. Simple, and fine while a link was just a link."),
    ("Then the link needed data", "The business wanted the enrolment date and how many lessons each student had done in each course. The mapping had no place for either: it writes the two ids and nothing else."),
    ("The fix", "Make the link an entity, <code>Enrolment</code>, with its own id, date and progress, two <code>@ManyToOne</code>s, and the pair unique in the database."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">When a link between two things has facts of its own, the link is a thing too.</p>

<h2>What are we building?</h2>
<p>A student enrols in a course (<code>POST /courses/{id}/enrolments</code>), reports lessons done (<code>PATCH /enrolments/{id}/progress</code>), and sees their courses with progress (<code>GET /students/{id}/courses</code>). Each student–course pair is one row with its own date and progress.</p>

<h2>An everyday analogy</h2>
<p>An airline could keep "Asha flies to Delhi" as a line in a list. Once it needs her seat and boarding time, it prints a boarding pass: a document for that one passenger on that one flight. <code>Enrolment</code> is the boarding pass.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Enrolling</strong> inserts one <code>enrolments</code> row: student, course, today's date, 0 lessons.</li>
<li><strong>The pair is unique</strong>, so a second enrolment of the same student in the same course is refused.</li>
<li><strong>Progress</strong> updates that row; the database checks it against the course's lesson count.</li>
<li><strong>Listing</strong> a student's courses reads their rows, with each course joined in.</li>
</ol>

<details class="qa check"><summary>Check yourself: why not add a <code>progress</code> column to <code>courses</code>?</summary><p>A course row is shared by every student in it. Progress belongs to one student in one course, so it can only live on the row for that pair.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No login.</strong> The student is named in the body.</li>
<li><strong>No lessons table.</strong> Progress is a count, not which lessons.</li>
<li><strong>No unenrolling.</strong> That is challenge 1.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Shikshalab</strong> (a fictional edtech platform) needs, for every student in every course, when they enrolled and how far they got. The old <code>@ManyToMany</code> mapping cannot hold either.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> Asha enrols in Spring Boot from zero, <b>then</b> <code>201</code>, today's date (India), 0 of 40 lessons.</li>
<li><b>Given</b> she reports 12 lessons, <b>then</b> 30%, and Rahul in the same course still has 0.</li>
<li><b>Given</b> she finishes all 8 lessons of Git basics, <b>then</b> 100% and a completion date; reporting 7 again clears it.</li>
<li><b>Given</b> she enrols twice, or 30 clicks arrive at once, <b>then</b> one enrolment; the others are <code>409</code>.</li>
<li><b>Given</b> 41 lessons of 40, <b>then</b> <code>422</code>; −1, missing or not a number, <code>400</code>; an unknown student in the body, <code>422</code>.</li>
<li><b>Given</b> an unknown course, enrolment or student in the path, <b>then</b> <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>One enrolment per student per course, enforced by a composite unique constraint.</li>
<li>Progress between 0 and the course's lessons, enforced by the database too.</li>
<li>A completion date exactly when every lesson is done, enforced by the database too.</li>
<li>Dates are Indian dates (<code>Asia/Kolkata</code>).</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Replace <code>@ManyToMany</code> with a join entity and two <code>@ManyToOne</code>s.</li>
<li>Put rules about a pair in the database: composite unique and composite foreign keys.</li>
<li>Explain why <code>@ManyToMany</code> fails for links with data, and what Hibernate does when one element is removed from a list.</li>
<li>Read a many-to-many from either side through the join entity.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/courses/{id}/enrolments</code>", "Enrol a student: <code>{\"studentId\": 1}</code>."],
    ["<code>PATCH</code>", "<code>/enrolments/{id}/progress</code>", "Report lessons done: <code>{\"lessonsCompleted\": 12}</code> (a total, not an increase)."],
    ["<code>GET</code>", "<code>/students/{id}/courses</code>", "The student's enrolments with course, progress and dates, oldest first."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "Enrolled; <code>Location</code> points at the enrolment"],
    ['<span class="pill ok">200</span>', "Progress recorded; or the list"],
    ['<span class="pill warn">400</span>', "Student missing; lessons missing, negative or not a number"],
    ['<span class="pill warn">404</span>', "No such course, enrolment or student in the path"],
    ['<span class="pill warn">409</span>', "Already enrolled in this course"],
    ['<span class="pill warn">422</span>', "Unknown student in the body; more lessons than the course has"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, against one fresh database. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-asha-enrols-in-spring-boot", "Case 1: Asha enrols in Spring Boot from zero", "<b>Why:</b> a new pair: today, 0 of 40."),
    ("02-and-in-git-basics", "Case 2: and in Git basics", "<b>Why:</b> a second row for the same student."),
    ("03-rahul-enrols-in-spring-boot", "Case 3: Rahul enrols in Spring Boot", "<b>Why:</b> a second row for the same course."),
    ("04-asha-has-done-12-lessons", "Case 4: Asha has done 12 lessons", "<b>Why:</b> her row only: 30%."),
    ("05-asha-finishes-git", "Case 5: Asha finishes Git basics", "<b>Why:</b> 8 of 8: completed today."),
    ("06-ashas-courses", "Case 6: Asha's courses", "<b>Why:</b> each with its own date and progress."),
    ("07-enrolled-twice", "Case 7: Asha enrols in Spring Boot again", "<b>Why:</b> the pair exists: <code>409</code>."),
    ("08-lesson-41-of-40", "Case 8: 41 lessons of 40", "<b>Why:</b> <code>422</code>."),
    ("09-no-such-student", "Case 9: student 99", "<b>Why:</b> <code>404</code>."),
]) + """
<h2>The join table</h2>
<p class="muted">Read with psql after the requests above (<code>docs/captures/rows.txt</code>).</p>
""" + code(read("docs/captures/rows.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A new enrolment", "Today, 0 lessons, <code>Location</code>", "<code>anEnrolmentStartsTodayAtZero</code>"],
    ["Two students in one course", "Each has their own progress", "<code>progressIsKeptPerStudentAndCourse</code>"],
    ["The last lesson, then one undone", "Completion date set, then cleared", "<code>theLastLessonCompletesTheCourseAndUndoingItReopens</code>"],
    ["A student's courses", "In enrolment order", "<code>aStudentsCoursesComeInEnrolmentOrder</code>"],
    ["Enrol twice", "<code>409</code>", "<code>enrollingTwiceIs409</code>"],
    ["Bad bodies; too many lessons; unknown student", "<code>400</code>; <code>422</code>; <code>422</code>", "<code>badRequestsAre400Or422</code>"],
    ["Unknown course, enrolment, student", "<code>404</code>", "<code>unknownCoursesEnrolmentsAndStudentsAre404</code>"],
    ["Duplicates, wrong lesson count, progress out of range, completion mismatch, written directly", "Refused by named constraints", "<code>namedConstraintsHoldWithoutJava</code>"],
    ["A course shrunk below someone's progress", "Refused, nothing changes; growing it follows into the rows", "<code>shrinkingACourseBelowSomeonesProgressIsRefusedWhole</code>"],
    ["30 clicks on Enrol at once", "One <code>201</code>, 29 <code>409</code>", "<code>thirtyClicksOnEnrolMakeOneEnrolment</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead"><code>@ManyToMany</code> for a link that needs its own data, with nowhere to store it.</p>
<p>The old mapping is kept in the tests as <code>OldStudent</code>: a <code>List&lt;Course&gt;</code> over the same <code>enrolments</code> table. Three tests show what it cannot do. Adding a course fails, because it writes only the two ids and the table needs a date and a lesson count. Reading works but sees titles only: Asha's 12 of 40 lessons are in the row and nowhere in the model. Removing one course is worse: for a list, Hibernate deletes all of the student's rows and re-inserts the ones left, with ids only. The SQL, from a run of that test (<code>docs/bag-removal-sql.txt</code>):</p>
""" + code(read("docs/bag-removal-sql.txt").rstrip(), "text") + """
<p>Here the re-insert fails and the transaction rolls back. On a join table with defaults instead of <code>NOT NULL</code>, it would have succeeded and silently reset every other course's date and progress.</p>
<p>While building, each part was undone once. Without setting the completion date, 1 test turned red; without the "beyond the course" check, 1 (the database refused it, as a <code>500</code> instead of a <code>422</code>). Without turning the unique violation into <code>409</code>, the 30-click test turned red in 2 of 3 full runs: a race test can miss, because the check before the insert answers most clicks. Removing that check turned nothing red: the constraint answers <code>409</code> on its own.</p>
</div>
""" + code(read(T + "ManyToManyTrapTest.java"), "java") + code(read(T + "OldStudent.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "EnrolmentController.java", dwn("Validates the bodies; <code>Location</code> on enrol.", "HTTP only.", "Progress below zero reaching the service.")),
    (J + "EnrolmentDesk.java", dwn("Enrols, records progress, lists a student's courses.",
        "The pair check is a fast path; the unique constraint is the guarantee, mapped to <code>409</code>.",
        "Two enrolments from a double click.")),
    (J + "Enrolment.java", dwn("The join entity: student, course, date, progress, completion.",
        "Two <code>@ManyToOne</code>s replace the <code>@ManyToMany</code>; the link has fields of its own.",
        "Progress with nowhere to live.",
        "<ul><li><code>courseLessons</code> copies the course's lesson count so the database can check progress against it.</li><li><code>recordProgress</code> sets or clears the completion date with the count.</li></ul>")),
    (J + "Repositories.java", "<p>Student, course and enrolment repositories; the enrolment queries join the course in.</p>"),
    (J + "Student.java", "<p>A student. No list of courses: the courses are read through enrolments.</p>"),
    (J + "Course.java", "<p>A course and its lesson count.</p>"),
    (M + "V1__students_courses_enrolments.sql", "<p>The tables and named constraints, including the composite foreign key to the course's lesson count.</p>"),
    (M + "V2__demo_school.sql", "<p>Two students, three courses.</p>"),
    (J + "LearningApplication.java", "<p>Entry point; a <code>Clock</code> in India time for dates.</p>"),
    ("src/main/resources/application.yaml", "<p>open-in-view off; schema validation; decimals refused for whole-number fields.</p>"),
]
tree = """stations/049-course-enrolments-with-progress/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/shikshalab/learning/
│   ├── EnrolmentController.java   ├── EnrolmentDesk.java   ├── Enrolment.java   ├── Repositories.java
│   ├── Student.java   ├── Course.java   └── LearningApplication.java
├── src/main/resources/
│   ├── application.yaml   └── db/migration/V1__students_courses_enrolments.sql, V2__demo_school.sql
├── src/test/java/com/shikshalab/learning/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs, the old mapping's SQL"""
codetab = belongs(["Set up and run: commands for Windows and macOS/Linux, troubleshooting", "Try it yourself",
                   "10. Complete working code, in the order a request travels", "11. Code explanation"],
                  "Level 2. Every command here was run and gave the results shown.") + """
<h2>Set up and run</h2>
""" + table(["You need", "Version", "Check with"], [
    ["JDK", "25 (recommended). JDK 21 also works, see below", "<code>java -version</code>"],
    ["Docker", "Docker Desktop (Windows, macOS) or Docker Engine (Linux), running", "<code>docker info</code>"],
    ["Maven", "Not needed: the project ships the Maven wrapper", ""]]) + """
<p><strong>macOS / Linux</strong></p>
""" + code("""docker compose up -d        # PostgreSQL 17 on localhost:5432
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests; starts its own PostgreSQL container""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>See the SQL behind the trap for yourself:</p>
""" + code("""./mvnw test -Dtest=ManyToManyTrapTest#droppingOneCourseRewritesTheWholeList -Dspring.jpa.show-sql=true""", "bash") + """
<p>Look for <code>delete from enrolments where student_id=?</code> followed by an insert of two columns. Then change <code>List&lt;Course&gt;</code> to <code>Set&lt;Course&gt;</code> in <code>OldStudent</code> and run it again: Hibernate can now delete the one row, and that test fails because nothing breaks (<code>delete from enrolments where student_id=? and course_id=?</code> was checked the same way). A set fixes the rewrite, not the missing date and progress.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>null value in column ... violates not-null constraint</code> on a join table", "A <code>@ManyToMany</code> writing a table that has more columns.", "Map the join table as an entity."],
    ["<code>delete from ... where student_id=?</code> when removing one element", "A <code>@ManyToMany</code> list (bag): Hibernate rewrites it.", "A join entity; or at least a <code>Set</code>."],
    ["<code>500</code> on a double click", "The unique violation is not mapped.", "Catch it by constraint name and answer <code>409</code>."],
    ["<code>enrolments_course_fk</code> when inserting directly", "<code>course_lessons</code> does not match the course.", "Copy the course's lesson count when enrolling."],
    ["Yesterday's date just after midnight", "Dates taken in UTC.", "A <code>Clock</code> in <code>Asia/Kolkata</code>."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the entities and the database.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>EnrolmentContractTest</code> ({cnt('EnrolmentContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>ManyToManyTrapTest</code> ({cnt('ManyToManyTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>EnrolmentDatabaseTest</code> ({cnt('EnrolmentDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "ManyToManyTrapTest.java", "<p>Written first: what the old <code>@ManyToMany</code> cannot write, cannot show, and does on removal.</p>"),
    (T + "EnrolmentContractTest.java", "<p>Enrol, progress, list, and every refusal.</p>"),
    (T + "EnrolmentDatabaseTest.java", "<p>Named constraints, a refused course change, and 30 clicks at once (virtual threads and a start latch).</p>"),
    (T + "OldStudent.java", "<p>The old mapping, kept only in tests.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: no enrolments before each test; today's date in India.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/shikshalab/learning/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=UnenrolChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Drop a course", "Beginner-friendly", 20,
    "Add <code>DELETE /enrolments/{id}</code>: <code>204</code>, and the course leaves the student's list while the others keep their progress. A completed course stays (<code>409</code>); unknown is <code>404</code>.",
    "both tests in <code>UnenrolChallengeTest</code> pass.",
    ["Deleting one <code>Enrolment</code> deletes one row: compare with the trap's rewrite.",
     "Check <code>completedOn</code> before deleting."],
    "challenge/UnenrolChallengeTest.java", ["challenge/solution/EnrolmentDesk.java", "challenge/solution/EnrolmentController.java"]) + challenge(2, "A course roster", "Go deeper", 25,
    "Add <code>GET /courses/{id}/students</code>: the students in a course with their progress, furthest along first, then by name.",
    "the test in <code>CourseRosterChallengeTest</code> passes.",
    ["A derived query on the join entity: <code>findByCourseIdOrderByLessonsCompletedDescStudentNameAsc</code>.",
     "Join the student in with an entity graph, so the roster is one query."],
    "challenge/CourseRosterChallengeTest.java", ["challenge/solution/Repositories.java", "challenge/solution/EnrolmentDesk.java", "challenge/solution/EnrolmentController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>When is <code>@ManyToMany</code> still fine?</h2>
<p>List three many-to-many links in apps you know (tags on posts, roles of users, products in categories, …). For each, decide whether the link will ever need its own data, how you would find out, and what migrating from <code>@ManyToMany</code> to a join entity would cost later.</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, mapping"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap tests with the old mapping on the new table.</li>
<li>Design the join table first: its own id, the pair, its own columns, and the rules on them.</li>
<li>Map it as an entity with two <code>@ManyToOne</code>s; drop the collections from <code>Student</code> and <code>Course</code>.</li>
<li>Query from either side through the join entity.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Join entity with its own id", "One more class; the pair needs a unique constraint.", '<span class="pill ok">Chosen</span>'],
    ["<code>@ManyToMany</code>", "No room for link data; a list rewrites the table on removal.", '<span class="pill bad">The trap</span>'],
    ["Join entity with a composite id (<code>@EmbeddedId</code>, <code>@MapsId</code>)", "No extra id column; more mapping code, ids of two parts in URLs.", '<span class="pill warn">Valid</span>'],
    ["Progress in a separate table keyed by student and course", "Two tables describing one link, kept in step by hand.", '<span class="pill bad">No</span>'],
    ["A JSON column of progress on the student", "No constraints, no joins, no per-course queries.", '<span class="pill bad">No</span>']]) + """
<h2>Database design</h2>
""" + table(["Table", "Constraints", "Mapped as"], [
    ["<code>enrolments</code>", "<code>enrolments_student_course_unique</code>, <code>enrolments_student_fk</code>, <code>enrolments_course_fk</code> (course and its lesson count), <code>enrolments_progress_range</code>, <code>enrolments_completed_when_done</code>", "<code>Enrolment</code>: <code>@ManyToOne</code> student and course"],
    ["<code>courses</code>", "<code>courses_lesson_count_range</code>, <code>courses_id_lessons_unique</code>", "<code>Course</code>"],
    ["<code>students</code>", "Primary key", "<code>Student</code>"]]) + """
""" + code(read(M + "V1__students_courses_enrolments.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Migrating from <code>@ManyToMany</code></dt><dd>Add the id and new columns to the existing join table in a migration, with values for old rows (an enrolment date you can defend, such as the first activity), then switch the mapping. The rows stay; their meaning grows.</dd>
<dt>Indexes on both sides</dt><dd>The unique constraint indexes (student, course), which serves "a student's courses". "A course's students" needs its own index on <code>course_id</code>.</dd>
<dt>Changing a course</dt><dd>The composite foreign key follows a new lesson count into every enrolment, and refuses one that would leave someone past the end. Decide with the content team what happens to those students first.</dd>
<dt>Progress from clients</dt><dd>A client reports a total, not "+1", so a retried request cannot count a lesson twice.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("When do you replace @ManyToMany with a join entity?", "As soon as the link has data of its own (a date, a role, a quantity, a status) or will be queried on its own. In practice, most business links end up there."),
    ("What does Hibernate do when you remove one element from a @ManyToMany List?", "For a bag (List without an order column), it deletes every row for the owner and re-inserts the remaining ones. A Set lets it delete just the one row."),
    ("How do you stop the same student enrolling twice?", "A unique constraint on (student_id, course_id). A check in code first is a nicety; the constraint holds under concurrent requests, and its violation becomes 409."),
    ("How can the database check progress against the course's lesson count?", "Copy the lesson count into the enrolment and tie it with a composite foreign key to (id, lesson_count) on courses, ON UPDATE CASCADE; then a CHECK compares the two columns of the same row."),
    ("Surrogate id or composite id for the join entity?", "A surrogate id is simpler to map and to put in URLs; a composite id avoids a column. Either way, the pair needs a unique constraint."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You saw the delete-all SQL yourself."],
    ["Mapping", "A join entity with two <code>@ManyToOne</code>s.", "You can say when <code>@ManyToMany</code> is still fine."],
    ["Integrity", "Unique pair; progress checked by the database.", "You can explain the composite foreign key."],
    ["Queries", "A student's courses in one query.", "The roster from the other side."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any many-to-many:</p>
<ul class="rules">
<li>Does the link have, or will it soon have, data of its own?</li>
<li>Is the pair unique in the database, not just in code?</li>
<li>If <code>@ManyToMany</code> stays, is it a <code>Set</code>, and what SQL runs when one element is removed?</li>
<li>Can both sides be queried without loading whole collections?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
