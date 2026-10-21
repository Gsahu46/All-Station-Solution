"""Station 077 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 77,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring Security 7 · request rules and @PreAuthorize · authorities as permissions · HTTP Basic",
    "simulation": "Staff, patients, notes and appointments are invented demo data held in memory, not Mediqo's and not real patients. Prescriptions are records in a list: nothing reaches a pharmacy.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No database and no Docker. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/mediqo/wards/"
T = "src/test/java/com/mediqo/wards/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Role", "A job: receptionist, nurse, doctor.", "The badge colour at a hospital.", "<code>ROLE_NURSE</code>"),
    ("Authority (permission)", "One thing a role may do.", "\"May enter the pharmacy.\"", "<code>notes:read</code>"),
    ("Least privilege", "Each role gets only what its work needs.", "The cleaner's key opens cupboards, not the drug safe.", "reception has <code>appointments:read</code> only"),
    ("Request rule", "A check in the filter chain on the URL and method, before any code runs.", "The guard at the ward door.", "<code>requestMatchers(...)</code>"),
    ("@PreAuthorize", "A check on a method, in the code, with access to its arguments.", "The nurse at the bedside who checks the wristband.", "<code>@ward.inCareOf(...)</code>"),
    ("401 and 403", "401: who are you? 403: we know, and you may not.", "No badge, against the wrong badge.", "Basic challenge; \"Not allowed\""),
]
STORY = [
    ("Buttons hidden, doors open", "Mediqo's ward app showed each role only its own buttons. The API behind it checked only that someone was signed in."),
    ("A receptionist reads notes", "A receptionist typed a notes URL she had seen in a link, and the API returned a patient's clinical notes."),
    ("The fix", "The API itself decides: each endpoint needs a permission, each role has only the permissions its work needs, and each clinical request is also checked against who is in the caller's care."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Hiding a button is a convenience. The check belongs where the data is.</p>

<h2>What are we building?</h2>
<p>Three endpoints for ward staff, each guarded twice: a permission rule at the door, and a per-patient rule in the code.</p>

<h2>An everyday analogy</h2>
<p>A hospital lift that skips the ICU floor for visitors is not security: the stairs still lead there. The lock is on the ICU door, and the nurse inside still checks who you are visiting.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Sign in</strong>: the staff member's username and password with every request.</li>
<li><strong>Door</strong>: the filter chain checks the endpoint's permission; unknown paths are refused.</li>
<li><strong>Bedside</strong>: <code>@PreAuthorize</code> checks the permission again and whether this patient is in the caller's care.</li>
<li><strong>Answer</strong>: only then does the code read or write.</li>
</ol>

<details class="qa check"><summary>Check yourself: Dr Bose is a doctor. Why can she not read Kavya Menon's notes?</summary><p>She has the permission, but Kavya is Dr Sharma's patient on Cardiology. The per-patient rule refuses it: <code>aDoctorCannotReadOrPrescribeForAnotherDoctorsPatient</code>. A role alone is not enough.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No database.</strong> Demo records live in memory.</li>
<li><strong>No sign-in design.</strong> HTTP Basic keeps the focus on authorization; tokens are stations 073 and 074.</li>
<li><strong>No row-level filtering in SQL.</strong> That is station 078.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Mediqo</strong> (a fictional hospital): a receptionist could read clinical notes, because every signed-in user could call every endpoint.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo staff: reception.anu; nurse.ritu (Cardiology) and nurse.joseph (Orthopaedics); dr.sharma (patients P-1001, P-1002) and dr.bose (P-2001).</p>
<ol class="gwt">
<li><b>Given</b> any staff member, <b>then</b> today's appointments; the reason only for nurses and doctors.</li>
<li><b>Given</b> a doctor and her own patient, or a nurse and a patient on her ward, <b>then</b> the notes.</li>
<li><b>Given</b> a doctor and her own patient, <b>then</b> a prescription is recorded (<code>201</code>).</li>
<li><b>Given</b> reception asking for notes, or a nurse prescribing, <b>then</b> <code>403</code>.</li>
<li><b>Given</b> another doctor's patient, another ward, or an unknown patient, <b>then</b> <code>403</code>.</li>
<li><b>Given</b> no or wrong credentials, <b>then</b> <code>401</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Permissions are checked by the API, in the filter chain and again in the code.</li>
<li>Roles hold the fewest permissions their work needs.</li>
<li>Paths without a rule are refused.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Model roles as sets of permissions.</li>
<li>Write request rules and <code>@PreAuthorize</code> rules, and say what each one can see.</li>
<li>Add a per-record rule (whose patient is this?) next to the role rule.</li>
<li>Tell 401 from 403, and test both.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Needs"], [
    ["<code>GET</code>", "<code>/appointments/today</code>", "<code>appointments:read</code> (everyone)"],
    ["<code>GET</code>", "<code>/patients/{id}/notes</code>", "<code>notes:read</code> (nurses, doctors), and the patient in your care"],
    ["<code>POST</code>", "<code>/patients/{id}/prescriptions</code>", "<code>prescriptions:write</code> (doctors), and your own patient. Body <code>{drug, doseMg, timesPerDay, days}</code>."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span> / <span class="pill ok">201</span>', "Read / prescription recorded"],
    ['<span class="pill warn">400</span>', "A prescription field missing or out of range"],
    ['<span class="pill warn">401</span>', "No or wrong credentials"],
    ['<span class="pill warn">403</span>', "The role lacks the permission; the patient is not in your care, or does not exist; a path with no rule"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-a-doctor-reads-her-patients-notes", "Case 1: a doctor reads her patient's notes", "<b>Why:</b> permission and care both hold."),
    ("02-reception-tries-the-same", "Case 2: reception tries the same URL", "<b>Why:</b> <code>403</code>: the incident, refused by the API."),
    ("03-reception-sees-todays-list", "Case 3: reception's view of today", "<b>Why:</b> who, when, with whom; the reason is clinical, so <code>null</code>."),
    ("04-a-nurse-sees-the-reasons-too", "Case 4: a nurse's view of today", "<b>Why:</b> clinicians see the reason."),
    ("05-a-nurse-on-another-ward", "Case 5: a nurse asks about another ward's patient", "<b>Why:</b> right role, wrong patient: <code>403</code>."),
    ("06-a-doctor-prescribes", "Case 6: a doctor prescribes for her patient", "<b>Why:</b> <code>201</code> with a Location."),
    ("07-a-nurse-tries-to-prescribe", "Case 7: a nurse tries to prescribe", "<b>Why:</b> no <code>prescriptions:write</code>: <code>403</code>."),
    ("08-another-doctors-patient", "Case 8: a doctor asks about another doctor's patient", "<b>Why:</b> <code>403</code>."),
    ("09-no-credentials", "Case 9: no credentials", "<b>Why:</b> <code>401</code> with a Basic challenge."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Own patient's notes", "<code>200</code>", "<code>aDoctorReadsTheirPatientsNotes</code>"],
    ["A nurse, her ward", "<code>200</code>", "<code>aNurseReadsNotesOfPatientsOnTheirWard</code>"],
    ["A doctor prescribes", "<code>201</code>, Location, drug name trimmed", "<code>aDoctorPrescribesForTheirPatient</code>"],
    ["Today's list by role", "Reason for clinicians only", "<code>everyoneSeesTodaysAppointmentsButOnlyCliniciansSeeTheReason</code>"],
    ["Bad prescriptions", "<code>400</code>", "<code>aBadPrescriptionIs400</code>"],
    ["Unknown patient", "<code>403</code>, like someone else's", "<code>anUnknownPatientIsAnsweredLikeSomeoneElsesPatient</code>"],
    ["No, wrong or unknown credentials", "<code>401</code>", "<code>noOrWrongCredentialsAre401</code>"],
    ["Another doctor's patient", "<code>403</code> to read and to prescribe", "<code>aDoctorCannotReadOrPrescribeForAnotherDoctorsPatient</code>"],
    ["Another ward", "<code>403</code>", "<code>aNurseCannotReadNotesFromAnotherWard</code>"],
    ["The controller called with no request rule in front", "Still refused by <code>@PreAuthorize</code>", "<code>theCodeRefusesEvenIfARequestRuleIsMissing</code>"],
    ["Paths and methods with no rule", "<code>403</code>", "<code>pathsWithoutARuleAreRefused</code>"],
    ["Odd patient ids", "<code>400</code> or <code>403</code>, never an error", "<code>oddPatientIdsAre403Or400NeverAnError</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Checking roles only in the UI, while every endpoint stays open.</p>
<ul>
<li><strong>Reception and notes.</strong> The old menu has no Notes button for reception. The URL still exists; the API now answers <code>403</code>.</li>
<li><strong>A nurse and prescriptions.</strong> No Prescribe button for nurses; the API now answers <code>403</code>.</li>
<li><strong>Reception and prescriptions.</strong> <code>403</code>.</li>
<li><strong>The control.</strong> Dr Sharma, for her own patient: notes and a prescription work.</li>
</ul>
<p>While building, each part was undone once. Dropping a request rule (notes or prescriptions) turned 0 tests red: <code>@PreAuthorize</code> still refused. Dropping <code>@PreAuthorize</code> on notes turned 5 red, an always-true care rule 5, no nurse-ward rule 1, no <code>@EnableMethodSecurity</code> 5, the reason shown to everyone 1, and <code>denyAll</code> replaced by <code>authenticated</code> 1.</p>
</div>
""" + code(read(T + "UiOnlyRolesTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "SecurityConfig.java", dwn("The door: one permission per endpoint, the staff and their roles.",
        "Request rules by method and path; everything else refused; <code>@EnableMethodSecurity</code> switches on the second line.",
        "A new endpoint open to every signed-in user, or a role with more than its work needs.",
        "<ul><li>Removing one request rule turned no test red, because <code>@PreAuthorize</code> still refused. Two lines of defence hide each other's gaps; only tests that bypass one line (calling the controller directly) show what the other adds. Found while building.</li><li>CSRF is off: credentials travel in a header with every request, never in a cookie a browser adds by itself.</li></ul>")),
    (J + "WardController.java", dwn("The bedside: each method's rule, next to the code it protects.",
        "<code>@PreAuthorize</code> repeats the permission and adds the per-patient rule; reception's view of the day leaves out the reason.",
        "A forgotten request rule exposing notes, or a doctor reading any patient's notes.")),
    (J + "Ward.java", dwn("The demo records, and the care rule.",
        "<code>inCareOf</code>: a doctor's own patients, a nurse's ward; an unknown patient is not in anyone's care.",
        "Probing patient ids by watching 403 against 404.",
        "<p><code>inCareOf</code> must be <code>public</code>: SpEL in <code>@PreAuthorize</code> calls public methods only, and otherwise fails with EL1004E \"method cannot be found\". Found while building.</p>")),
    (J + "ProblemResponses.java", "<p>401 with a Basic challenge and 403 in the same problem JSON as every other error.</p>"),
    ("src/main/resources/application.yaml", "<p>Problem details on; nothing else to configure.</p>"),
    (J + "WardsApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/077-hospital-staff-roles/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/mediqo/wards/
│   ├── SecurityConfig.java   ├── WardController.java   ├── Ward.java
│   ├── ProblemResponses.java   └── WardsApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/mediqo/wards/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs"""
codetab = belongs(["Set up and run: commands for Windows and macOS/Linux, troubleshooting", "Try it yourself",
                   "10. Complete working code, in the order a request travels", "11. Code explanation"],
                  "Level 2. Every command here was run and gave the results shown.") + """
<h2>Set up and run</h2>
""" + table(["You need", "Version", "Check with"], [
    ["JDK", "25 (recommended). JDK 21 also works, see below", "<code>java -version</code>"],
    ["Docker", "Not needed", ""],
    ["Maven", "Not needed: the project ships the Maven wrapper", ""]]) + """
<p><strong>macOS / Linux</strong></p>
""" + code("""./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code(""".\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>The same URL, three people:</p>
""" + code("""for who in dr.sharma:sharma-demo-pass nurse.joseph:joseph-demo-pass reception.anu:anu-demo-pass; do
  curl -s -o /dev/null -w "${who%%:*} %{http_code}\\n" -u "$who" http://localhost:8080/patients/P-1001/notes
done""", "bash") + """
<p>It prints <code>dr.sharma 200</code>, <code>nurse.joseph 403</code> (another ward) and <code>reception.anu 403</code>.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>EL1004E: Method call: Method inCareOf(...) cannot be found</code>", "The bean method used in <code>@PreAuthorize</code> is not public.", "Make it public. Found while building this station."],
    ["<code>@PreAuthorize</code> seems to do nothing", "Method security is not switched on.", "Add <code>@EnableMethodSecurity</code>: without it the annotations are ignored, silently."],
    ["<code>403</code> on a new endpoint", "<code>denyAll()</code> at the end of the chain.", "Add a request rule and a <code>@PreAuthorize</code>, on purpose."],
    ["<code>#patientId</code> is null in the rule", "Parameter names were not compiled in.", "Spring Boot's Maven parent compiles with <code>-parameters</code>; keep it, or name the parameter in the expression's source."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>WardContractTest</code> ({cnt('WardContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>UiOnlyRolesTrapTest</code> ({cnt('UiOnlyRolesTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, one user accessing another user's data, malicious input", f"<code>WardSecurityTest</code> ({cnt('WardSecurityTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">\"Not found\" here is the unknown patient, answered like someone else's on purpose. \"Another user's data\": another doctor's patient and another ward's patient.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, Spring Security 7.1. No Docker. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "UiOnlyRolesTrapTest.java", "<p>Written first: what the old menu hid, and the same calls made directly.</p>"),
    (T + "WardSecurityTest.java", "<p>401, other patients and wards, the code's own refusal without a request rule, paths with no rule, odd ids.</p>"),
    (T + "WardContractTest.java", "<p>Notes, prescriptions and appointments through HTTP.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: request helpers with HTTP Basic.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/mediqo/wards/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=NotesAuditChallengeTest</code>.</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Who read which notes", "Beginner-friendly", 25,
    "Record every read of clinical notes (staff, patient). <code>GET /audit/notes-reads</code> lists them for the privacy officer <code>admin.meena</code> (permission <code>audit:read</code>) only.",
    "both tests in <code>NotesAuditChallengeTest</code> pass.",
    ["A new permission and a new user; a request rule and a <code>@PreAuthorize</code> for the new path.",
     "Record inside the notes method, after the rule has passed."],
    "challenge/NotesAuditChallengeTest.java", ["challenge/solution/Ward.java", "challenge/solution/WardController.java", "challenge/solution/SecurityConfig.java"]) + challenge(2, "Break-glass for emergencies", "Go deeper", 35,
    "A doctor may read the notes of a patient not in their care by sending <code>X-Emergency-Reason</code> (10 to 200 characters); the audit marks it as an emergency, with the reason. Nurses cannot, and a short reason does not count.",
    "both tests in <code>BreakGlassChallengeTest</code> pass (after challenge 1).",
    ["Add <code>or @ward.breakGlass(authentication)</code> to the rule; the bean can read the header from <code>RequestContextHolder</code>.",
     "Keep the controller method's signature: a test calls it directly."],
    "challenge/BreakGlassChallengeTest.java", ["challenge/solution/Ward.java", "challenge/solution/WardController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Roles from the hospital directory</h2>
<p>Staff join, move wards and leave every week. Design how roles and wards come from the hospital's directory (groups in Active Directory or another LDAP server) instead of code, how fast a removal takes effect, and how a quarterly access review would find a nurse who still reads notes on a ward she left.</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: what the menu hid, called directly.</li>
<li>Turn roles into sets of permissions.</li>
<li>One request rule per endpoint; <code>denyAll</code> for the rest.</li>
<li><code>@PreAuthorize</code> on each method, with the per-patient rule.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Permissions per role, request rules plus @PreAuthorize", "Rules in two places to keep in step.", '<span class="pill ok">Chosen</span>'],
    ["Roles checked in the UI only", "Anyone with a URL gets everything.", '<span class="pill bad">The trap</span>'],
    ["Request rules only", "Cannot see whose record it is.", '<span class="pill warn">Not enough for per-patient rules</span>'],
    ["@PreAuthorize only", "A method without the annotation is open.", '<span class="pill warn">One forgotten line away</span>'],
    ["A policy engine (OPA, Cedar) or relationship-based access", "Another system; rules out of code, easy to audit.", '<span class="pill warn">At scale; see station 079</span>']]) + """
<h2>Database design</h2>
<p>No database in this station: the demo records are in memory. In a real system, \"in care of\" comes from the care-team and ward-assignment tables, and station 078 shows how to put such a rule into the query itself.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Audit</dt><dd>Health data access is usually audited by law: who read which record, when. Challenge 1 builds the start of it.</dd>
<dt>Emergencies</dt><dd>A rule that blocks a doctor in A&amp;E costs more than it saves: break-glass with a recorded reason (challenge 2), reviewed afterwards.</dd>
<dt>Directory</dt><dd>Roles and wards belong in the hospital's directory, not in code; removals must take effect within minutes.</dd>
<dt>Logs</dt><dd>Never log note text or prescription bodies.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Role or authority?", "A role is a job; an authority is one permission. Check authorities in code, and map roles to them, so a new role does not mean editing every rule."),
    ("Request rules or @PreAuthorize?", "Request rules guard paths before any code runs; @PreAuthorize sees the method's arguments and can check the record. Use both: the first as a default, the second for per-record rules."),
    ("Why answer 403 for an unknown patient?", "So nobody can tell which ids exist by comparing answers. The same reason sign-in gives one answer for unknown users and wrong passwords."),
    ("What does @EnableMethodSecurity do?", "It switches method security on. Without it, @PreAuthorize annotations are ignored, silently."),
    ("What is least privilege?", "Each role gets only the permissions its work needs, so a stolen or misused account can do as little as possible."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Roles", "Permissions per role.", "Least privilege, down to the fields reception sees."],
    ["Rules", "Request rules and denyAll.", "@PreAuthorize with a per-record rule, tested without the request rule."],
    ["Privacy", "No notes for reception.", "Unknown and someone else's patient look the same."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("Method security switched off",
     "\"@PreAuthorize does the rest\", but <code>@EnableMethodSecurity</code> was removed with the duplicate rules. Every annotation in the controller is now ignored, and the only rule left is \"signed in\": the original incident, with annotations that look like protection.",
     "<code>receptionCouldReadClinicalNotesByCallingTheApi</code>, <code>aNurseCouldPrescribeByCallingTheApi</code>, <code>receptionCouldPrescribeToo</code>, <code>aDoctorCannotReadOrPrescribeForAnotherDoctorsPatient</code>, <code>aNurseCannotReadNotesFromAnotherWard</code>, <code>theCodeRefusesEvenIfARequestRuleIsMissing</code>, <code>anUnknownPatientIsAnsweredLikeSomeoneElsesPatient</code> and <code>oddPatientIdsAre403Or400NeverAnError</code> fail."),
    ("authenticated() instead of denyAll",
     "Paths nobody wrote a rule for are now open to every member of staff.",
     "<code>pathsWithoutARuleAreRefused</code> fails."),
    ("The reason shown to reception",
     "Why a patient comes is clinical information; planning the waiting room needs the time and the doctor.",
     "<code>everyoneSeesTodaysAppointmentsButOnlyCliniciansSeeTheReason</code> fails."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate removes \"duplicated\" security: the request rules go, since the controller already has <code>@PreAuthorize</code>, and the chain becomes one <code>authenticated()</code> rule. Reception also asked to see why patients come. Read the two files and list every problem before opening the findings.</p>
<p class="path">review/SecurityConfig.java</p>
""" + code(read("review/SecurityConfig.java"), "java") + """
<p class="path">review/WardController.java</p>
""" + code(read("review/WardController.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the two flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">The controller still reads as if it were protected. Nothing in a code review of that file alone shows the annotations are dead.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
