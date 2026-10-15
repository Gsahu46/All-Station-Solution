"""Station 043 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 43,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring Data JPA · Hibernate 7 · @Entity, JpaRepository, derived queries, @EntityGraph · DTO records · PostgreSQL 17 · Flyway · Testcontainers",
    "simulation": "Doctors, clinics, phone numbers, salaries and notes are fictional demo data. The private columns exist so the trap test can show what leaks.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/mediqo/doctors/"
T = "src/test/java/com/mediqo/doctors/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("JPA", "A standard way to map Java classes to tables, so you work with objects instead of SQL rows.", "A translator between your language and the database's.", "<code>jakarta.persistence</code>"),
    ("Entity", "A class whose objects are rows of a table, managed by Hibernate.", "A file card that is also the record in the cabinet.", "<code>Doctor</code>"),
    ("Repository", "An interface; Spring Data writes the code behind it.", "Asking the librarian instead of searching the shelves.", "<code>DoctorRepository</code>"),
    ("Derived query", "A query written from a method's name.", "\"Find by speciality and city, ordered by name\".", "<code>findBySpecialityIgnoreCaseAndCity…</code>"),
    ("DTO", "A plain object shaped for the API, separate from the entity.", "The visiting card, not the HR file.", "<code>DoctorView</code>"),
    ("Lazy loading", "A linked object is fetched only when first touched, while the session is open.", "A file fetched from storage when you ask, if the archive is still open.", "<code>Doctor.clinic</code>"),
]
STORY = [
    ("A week per filter", "Every doctor search was SQL written by hand. Adding \"speciality\" meant new SQL, new mapping, new tests: a week."),
    ("JPA, returned as is", "The team switched to JPA and returned the Doctor entity straight from the controller. Some requests failed with a lazy-loading error. The others sent each doctor's personal phone, salary and HR notes to every visitor of the public directory."),
    ("The fix", "Entities stay inside the service. The API returns a small record with only what the directory shows, built while the database session is open."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">The API's shape is a decision. Never let it be whatever the table happens to hold.</p>

<h2>What are we building?</h2>
<p><code>GET /doctors?speciality=…&amp;city=…</code> searches the public directory, and <code>GET /doctors/{id}</code> shows one doctor: name, speciality, city, registration number and clinic.</p>

<h2>An everyday analogy</h2>
<p>A hospital's notice board shows each doctor's name, speciality and room. The HR file with salary and home phone stays in the office. You copy what the board needs onto the board; you do not pin up the file.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Pick a repository method</strong> for the filters given; Spring Data has written its query.</li>
<li><strong>Load doctors and their clinics</strong> in one query.</li>
<li><strong>Copy each into a <code>DoctorView</code></strong>, inside the transaction.</li>
<li><strong>Return the views</strong>; the entities never reach the JSON writer.</li>
</ol>

<details class="qa check"><summary>Check yourself: if the entity has a <code>@JsonIgnore</code> on salary, is returning it fine?</summary><p>Safer, but fragile: the next private column added to the table is public until someone remembers to hide it, and the lazy clinic can still fail. A DTO lists what is public; everything else is private by default.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>Read-only.</strong> No adding or editing doctors here.</li>
<li><strong>No appointments.</strong> Just the directory.</li>
<li><strong>No full-text search.</strong> Exact speciality and city, any letter case.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Mediqo</strong> (a fictional clinic chain) wrote SQL by hand for every doctor search; adding a speciality filter took a week.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> <code>speciality=cardiology&amp;city=PUNE</code>, <b>then</b> Dr Asha Mehta and Dr Fatima Ali, by name.</li>
<li><b>Given</b> only a speciality, only a city, or neither, <b>then</b> the matching doctors; a speciality nobody has, an empty list.</li>
<li><b>Given</b> doctor 1, <b>then</b> exactly id, name, speciality, city, registration number, clinic and clinic address; no personal phone, salary or notes anywhere.</li>
<li><b>Given</b> a search of all doctors, <b>then</b> one database query, not one more per clinic.</li>
<li><b>Given</b> an unknown doctor, <code>404</code>; a filter with digits or over 40 characters, or a non-numeric id, <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Entities never leave the service; the API returns <code>DoctorView</code>.</li>
<li><code>open-in-view</code> is off: no database access while JSON is written.</li>
<li>Flyway owns the schema; Hibernate only validates it.</li>
<li>Rules stay database constraints too: unique registration number, valid clinic, positive salary.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Map tables with <code>@Entity</code>, <code>@Id</code> and <code>@ManyToOne</code>.</li>
<li>Use <code>JpaRepository</code> and derived query methods.</li>
<li>Separate entities from DTOs, and say why.</li>
<li>Explain lazy loading, <code>open-in-view</code>, and N+1 queries.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/doctors?speciality=…&amp;city=…</code>", "Doctors in the directory; both filters optional, any letter case."],
    ["<code>GET</code>", "<code>/doctors/{id}</code>", "One doctor."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "A list (possibly empty) or one doctor"],
    ['<span class="pill warn">400</span>', "A filter that is not 2 to 40 letters and spaces, or a non-numeric id"],
    ['<span class="pill warn">404</span>', "No such doctor"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-cardiologists-in-pune", "Case 1: cardiology in Pune", "<b>Why:</b> a derived query with two IgnoreCase conditions."),
    ("02-every-cardiologist", "Case 2: cardiology anywhere", "<b>Why:</b> another derived method; each doctor's clinic came in the same query."),
    ("03-one-doctor", "Case 3: doctor 1", "<b>Why:</b> the view: what the directory shows, nothing else."),
    ("04-no-such-doctor", "Case 4: doctor 99", "<b>Why:</b> <code>404</code>."),
    ("05-a-filter-with-a-digit", "Case 5: <code>Cardio1ogy</code>", "<b>Why:</b> <code>400</code>, before the database."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Both filters, mixed case", "Two doctors, by name", "<code>bothFiltersInAnyCase</code>"],
    ["One filter; none; nobody matches", "The right doctors; all six; empty", "<code>oneFilterOrNone</code>"],
    ["One doctor; any list", "Exactly the view's fields; no phone digits anywhere", "<code>oneDoctorAsTheDirectoryShowsThem</code>"],
    ["Searching every doctor", "1 query (3 without the entity graph)", "<code>aSearchLoadsDoctorsAndClinicsInOneQuery</code>"],
    ["Duplicate registration, unknown clinic, zero salary, written directly", "Refused by named constraints", "<code>namedConstraintsHoldWithoutJava</code>"],
    ["An import with a duplicate", "Rolled back", "<code>aFailedImportLeavesTheDirectoryAsItWas</code>"],
    ["Unknown doctor; bad filters or id", "<code>404</code>; <code>400</code>", "<code>DoctorContractTest</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Returning entities directly as JSON, leaking fields and lazy-loading errors.</p>
<p>The test writes a <code>Doctor</code> entity with the app's own JSON mapper (Jackson 3), as the old controller did. Outside a transaction (open-in-view off), the lazy clinic cannot be loaded: <code>LazyInitializationException … no session</code>. Inside one (what open-in-view on would do), the JSON contains <code>personalPhone</code>, <code>salaryPaise</code>, <code>internalNotes</code>, and Hibernate's own <code>hibernateLazyInitializer</code>. A probe while building found a third outcome. With package-private getters on <code>Clinic</code>, the proxy was written as <code>{"hibernateLazyInitializer":{}}</code> with no error at all. Entities usually have public getters, so this station uses them and shows the two common outcomes. While building, adding the personal phone to the view turned 2 tests red. Removing the entity graph from the full list turned 1 red: 3 queries instead of 1.</p>
</div>
""" + code(read(T + "EntityAsJsonTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "DoctorController.java", dwn("Validates the filters and returns views.",
        "It never sees an entity.",
        "Returning <code>Doctor</code>: the trap.")),
    (J + "DoctorDirectory.java", dwn("Chooses the repository method and maps to <code>DoctorView</code>.",
        "<code>@Transactional(readOnly = true)</code>: the mapping runs while the session is open.",
        "Mapping in the controller after the session closed: lazy-loading errors.")),
    (J + "DoctorRepository.java", dwn("Derived query methods, each with an entity graph.",
        "A new filter is a new method name; <code>@EntityGraph</code> joins the clinic so there is one query.",
        "One query for doctors plus one per clinic (N+1).",
        "<ul><li><code>IgnoreCase</code> becomes <code>upper(…) = upper(…)</code> in SQL.</li><li><code>findWithClinicById</code>: words between <code>find</code> and <code>By</code> are free text, so the method can be named for what it does.</li></ul>")),
    (J + "DoctorView.java", dwn("What the directory shows.",
        "Fields are listed on purpose; new private columns stay private.",
        "Every column of the table in the public API.")),
    (J + "Doctor.java", dwn("The doctors table as an entity, with a lazy link to the clinic.",
        "Hibernate tracks and loads it; <code>protected</code> no-argument constructor for JPA.",
        "Nothing to map rows to.")),
    (J + "Clinic.java", "<p>The clinics table as an entity.</p>"),
    (M + "V1__clinics_and_doctors.sql", "<p>Both tables, named constraints, and an index for the search.</p>"),
    (M + "V2__demo_directory.sql", "<p>Two clinics and six doctors.</p>"),
    ("src/main/resources/application.yaml", "<p><code>open-in-view: false</code> and <code>ddl-auto: validate</code>, with why.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "DoctorsApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/043-doctor-directory-with-jpa/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/mediqo/doctors/
│   ├── DoctorController.java   ├── DoctorDirectory.java   ├── DoctorRepository.java
│   ├── DoctorView.java   ├── Doctor.java   ├── Clinic.java   └── DoctorsApplication.java
├── src/main/resources/
│   ├── application.yaml
│   └── db/migration/   V1__clinics_and_doctors.sql, V2__demo_directory.sql
├── src/test/java/com/mediqo/doctors/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs"""
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
<p>See the SQL Spring Data writes for a method name. Start the app with SQL logging on, then search:</p>
""" + code("""./mvnw spring-boot:run -Dspring-boot.run.arguments=--logging.level.org.hibernate.SQL=debug
curl "http://localhost:8080/doctors?speciality=cardiology&city=pune\"""", "bash") + """
<p>The log shows one <code>select … from doctors … join clinics …</code> with <code>upper(…)</code> on both filters.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>LazyInitializationException: Could not initialize proxy … no session</code>", "A lazy link was touched after the transaction ended.", "Map to a DTO inside the transaction, or load the link with <code>@EntityGraph</code>."],
    ["<code>Schema-validation: missing column</code>", "An entity field has no matching column.", "Add a Flyway migration; <code>ddl-auto: validate</code> never changes the schema."],
    ["<code>No property 'specialty' found for type 'Doctor'</code>", "A derived method name does not match a field.", "Method names must spell the field exactly."],
    ["<code>Could not find a valid Docker environment</code>", "Docker is not running.", "Start Docker, then run the tests again."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>DoctorContractTest</code> ({cnt('DoctorContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>EntityAsJsonTrapTest</code> ({cnt('EntityAsJsonTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>DoctorDatabaseTest</code> ({cnt('DoctorDatabaseTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, Hibernate 7, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "EntityAsJsonTrapTest.java", "<p>Written first: the entity as JSON outside and inside a transaction, and the view.</p>"),
    (T + "DoctorContractTest.java", "<p>Searches, one doctor, and refusals through HTTP.</p>"),
    (T + "DoctorDatabaseTest.java", "<p>Named constraints, a rollback, and the query count from Hibernate's statistics.</p>"),
    (T + "ApiTest.java", "<p>Shared setup, with Hibernate statistics on.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/mediqo/doctors/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=ClinicDoctorsChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "A clinic's doctors", "Beginner-friendly", 20,
    "Add <code>GET /clinics/{id}/doctors</code>: the clinic's doctors by name, as views. An unknown clinic is <code>404</code>, not an empty list.",
    "both tests in <code>ClinicDoctorsChallengeTest</code> pass.",
    ["A derived query can follow the link: <code>findByClinicIdOrderByName</code>.",
     "A small <code>ClinicRepository</code> gives you <code>existsById</code> for the 404."],
    "challenge/ClinicDoctorsChallengeTest.java", ["challenge/solution/DoctorRepository.java", "challenge/solution/ClinicRepository.java", "challenge/solution/DoctorController.java"]) + challenge(2, "Doctors per speciality", "Go deeper", 25,
    "Add <code>GET /specialities</code>: each speciality and its number of doctors, most first, then by name, counted by the database.",
    "the test in <code>SpecialityCountChallengeTest</code> passes.",
    ["A JPQL <code>@Query</code> with <code>group by</code> and aliases.",
     "An interface projection (<code>getSpeciality()</code>, <code>getDoctors()</code>) receives the aliased columns."],
    "challenge/SpecialityCountChallengeTest.java", ["challenge/solution/DoctorRepository.java", "challenge/solution/DoctorController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>When method names stop scaling</h2>
<p>Product wants filters for speciality, city, language spoken, gender, fee range and availability, in any combination. Derived methods would need 64 names. Compare JPA Specifications, Querydsl, Query by Example and a hand-written SQL builder with parameters. Which keeps queries type-safe, which keeps them readable, and which makes indexes easy to plan?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, mapping"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the schema in Flyway; set Hibernate to validate it.</li>
<li>Write the entities and the repository's derived methods.</li>
<li>Write the trap test: the entity as JSON, in and out of a transaction.</li>
<li>Write the view and the service that maps inside a transaction; count the queries.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Entities in the service, DTO records in the API", "A small mapping per view.", '<span class="pill ok">Chosen</span>'],
    ["Return entities, hide fields with <code>@JsonIgnore</code>", "New columns are public by default; lazy links still fail.", '<span class="pill bad">Fragile</span>'],
    ["<code>open-in-view: true</code>", "Lazy links load during JSON writing: hidden queries, connections held for the whole response.", '<span class="pill bad">Hides problems</span>'],
    ["<code>FetchType.EAGER</code> on the clinic", "Every load of a doctor loads the clinic, wanted or not.", '<span class="pill warn">Rarely right</span>'],
    ["Interface projections straight from the repository", "No entity at all for read-only views.", '<span class="pill warn">Good for reads (challenge 2)</span>']]) + """
<h2>Database design</h2>
""" + table(["Table", "Key and constraints", "Mapped as"], [
    ["<code>clinics</code>", "PK <code>id</code>", "<code>@Entity Clinic</code>"],
    ["<code>doctors</code>", "PK <code>id</code>, <code>doctors_registration_unique</code>, <code>doctors_clinic_fk</code>, <code>doctors_salary_positive</code>; index on <code>upper(speciality), upper(city)</code>", "<code>@Entity Doctor</code>, <code>@ManyToOne(fetch = LAZY)</code> to <code>Clinic</code>"]]) + """
<p class="muted">The index uses <code>upper()</code> because that is what the generated SQL compares (see Set up &amp; code); an index on <code>lower()</code>, the first version, could never have been used. Hibernate maps <code>registrationNumber</code> to <code>registration_number</code> by Spring Boot's naming strategy. <code>ddl-auto: validate</code> stops the app at startup if they ever disagree.</p>
""" + code(read(M + "V1__clinics_and_doctors.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Data exposure</dt><dd>A leaked column is a data breach. Review API responses as carefully as SQL: what fields leave the server?</dd>
<dt>Query counts</dt><dd>N+1 queries are invisible in development and painful in production. Count queries in tests, as this station does, for pages that list things.</dd>
<dt>open-in-view</dt><dd>Spring Boot enables it by default and logs a warning at startup. Turning it off early is easy; turning it off late breaks code that relied on it.</dd>
<dt>Schema ownership</dt><dd>Flyway changes the schema; <code>ddl-auto: validate</code> only checks. Never let Hibernate create or update production tables.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why not return JPA entities from a REST controller?", "They expose every mapped column, including private ones, tie the API to the table, and can trigger lazy loading (extra queries or LazyInitializationException) while JSON is written. Return DTOs."),
    ("What is open-in-view, and why turn it off?", "It keeps the persistence session open until the response is written, so lazy links load in the view layer. That hides N+1 queries and holds a connection for the whole request. Off makes problems visible."),
    ("What is the N+1 problem?", "One query for a list, then one more per item to load a link. Fix it with a fetch join or an entity graph."),
    ("How do derived query methods work?", "Spring Data parses the method name (findBy + properties + keywords like IgnoreCase, OrderBy) and generates the query at startup; a misspelt property fails startup."),
    ("Entity vs DTO?", "An entity is a managed row: identity, lazy links, change tracking. A DTO is a plain value shaped for one use, such as an API response."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You logged the SQL for a derived method."],
    ["JPA", "Entities, repository, derived queries.", "Entity graphs and query counting."],
    ["API design", "DTOs, never entities.", "Why @JsonIgnore is not enough."],
    ["Sessions", "open-in-view off.", "Exactly when a lazy link can be loaded."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any JPA endpoint:</p>
<ul class="rules">
<li>Does any controller return an <code>@Entity</code>?</li>
<li>Is <code>open-in-view</code> off, and does the mapping happen inside a transaction?</li>
<li>How many queries does the list endpoint run for 50 items?</li>
<li>Does Hibernate validate the schema, or change it?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
