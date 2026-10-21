"""Station 079 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 79,
    "stack": "Spring Boot 4.1.1 · Java 25 · Zanzibar-style relation tuples · recursive CTEs · Spring Security 7 (HTTP Basic) · JdbcClient · PostgreSQL 17 · Testcontainers",
    "simulation": "Users, teams, folders and documents are demo data, not Taskloom's. Share notices are rows in a table: no email is sent.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/taskloom/sharing/"
T = "src/test/java/com/taskloom/sharing/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Relation tuple", "One fact: object, relation, subject. \"team design is viewer of folder Brand.\"", "One line in a guest list.", "<code>relation_tuples</code>"),
    ("Userset", "\"Every member of a team\" used as one subject.", "\"The whole design team\" on the guest list.", "<code>team:design#member</code>"),
    ("Inheritance", "Access to a folder is access to what is inside it.", "A key to the building opens the hallway too.", "<code>parent</code> tuples"),
    ("ReBAC", "Relationship-based access control: access worked out from relationships, not stored per document.", "\"Friends of the host may come in.\"", "<code>Permissions.access</code>"),
    ("Recursive CTE", "One SQL query that follows links until there are no new ones.", "Asking \"and who is in that team?\" until nobody new turns up.", "<code>WITH RECURSIVE</code>"),
    ("Zanzibar", "Google's paper (2019) on one permission system for many products; OpenFGA and SpiceDB follow it.", "One guest list service for every party.", "the model here, in plain PostgreSQL"),
]
STORY = [
    ("Thirty checks", "Taskloom checked sharing with hand-written SQL in 30 places, each slightly different."),
    ("Copied access", "Sharing a folder with a team wrote a \"may read\" row for every member onto every document, at that moment. When Asha left the design team, her rows stayed: she opened its documents for a week."),
    ("The fix", "Every permission is one relationship. Access is worked out from the relationships on every request, so removing Asha from the team removes everything that came from it, at once."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Store why someone has access, not that they have it. Then taking the reason away takes the access.</p>

<h2>What are we building?</h2>
<p>Open a document, share it with a person or a team, and list what has been shared with you; all three answer from one table of relationships.</p>

<h2>An everyday analogy</h2>
<p>A club does not print a member card for each event. The door checks: are you a member, or the guest of one, today? Leave the club and every door knows at once.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Who are you?</strong> You, plus every team you are in, through teams inside teams.</li>
<li><strong>What is this?</strong> The document, plus every folder above it.</li>
<li><strong>Is there a link?</strong> Any owner, editor or viewer tuple from the first set to the second.</li>
<li><strong>Answer</strong>: the strongest one, or 404 if none.</li>
</ol>

<details class="qa check"><summary>Check yourself: Neha was never shared anything directly. Why can she open the logo brief?</summary><p>She is in brand-leads, which is in design; design may view the Brand folder; Logos is inside Brand; the brief is inside Logos. Four tuples, one query: <code>accessFlowsThroughFoldersAndTeamsInTeams</code>.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No permission service.</strong> The model is Zanzibar's, but it runs in this app's PostgreSQL. OpenFGA and SpiceDB are compared in Design.</li>
<li><strong>No team admin screen.</strong> Tests and captures change teams with one SQL statement.</li>
<li><strong>No editing.</strong> Documents are read and shared, not changed.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Taskloom</strong> (a fictional team tool): sharing was checked in 30 places, and a user removed from a team kept its documents for a week.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo workspace: ravi owns four documents; the Brand folder (with Logos inside) is shared with team design (asha, and team brand-leads with neha); meera edits the roadmap; kabir has nothing.</p>
<ol class="gwt">
<li><b>Given</b> a document in a folder shared with your team, or a team inside it, <b>then</b> you can open it as viewer.</li>
<li><b>Given</b> an editor or owner, <b>then</b> they can share with a user or a team (<code>201</code>); a viewer gets <code>403</code>.</li>
<li><b>Given</b> no relationship at all, <b>then</b> <code>404</code>, as for a document that does not exist.</li>
<li><b>Given</b> someone leaves a team, <b>then</b> the next request no longer finds the team's documents.</li>
<li><b>Given</b> a document added to a shared folder later, <b>then</b> the team can open it.</li>
<li><b>Given</b> \"shared with me\", <b>then</b> what you can open and do not own, with your access.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>One table of relationships; every check reads it; nothing is copied.</li>
<li>The database refuses relations that make no sense for an object type.</li>
<li>A share and its notice are one transaction.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Model permissions as tuples, with usersets and inheritance.</li>
<li>Check access with one recursive query, and know why it terminates.</li>
<li>Explain why copied permissions go stale.</li>
<li>Compare your own tables with OpenFGA or SpiceDB.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/docs/{id}</code>", "The document and <code>yourAccess</code>: viewer, editor or owner."],
    ["<code>POST</code>", "<code>/docs/{id}/shares</code>", "<code>{subject, relation}</code>: subject <code>user:name</code> or <code>team:name</code>, relation viewer or editor."],
    ["<code>GET</code>", "<code>/me/shared-with-me</code>", "Documents you can open and do not own, with your access."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span> / <span class="pill ok">201</span>', "Read / shared"],
    ['<span class="pill warn">400</span>', "A subject or relation of the wrong shape; an unknown user or team"],
    ['<span class="pill warn">401</span>', "No or wrong credentials"],
    ['<span class="pill warn">403</span>', "A viewer sharing; a path with no rule"],
    ['<span class="pill warn">404</span>', "No relationship to the document, or no such document"]]) + """
<h2>The demo tuples</h2>
<p class="muted">From <code>psql</code> in <code>docs/capture.sh</code>, before the requests below. This is the whole permission state.</p>
""" + code(read("docs/captures/tuples.txt").rstrip(), "text") + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-asha-opens-a-doc-in-the-team-folder", "Case 1: Asha opens a document in the team's folder", "<b>Why:</b> asha → design → viewer of Brand → the document."),
    ("02-neha-through-a-team-in-a-team", "Case 2: Neha opens the logo brief", "<b>Why:</b> through a team inside a team and a folder inside a folder."),
    ("03-shared-with-asha", "Case 3: shared with Asha", "<b>Why:</b> both documents from the folder, none of ravi's others."),
    ("04-kabir-before-any-share", "Case 4: Kabir asks for the roadmap", "<b>Why:</b> no relationship: <code>404</code>."),
    ("05-meera-shares-the-roadmap-with-kabir", "Case 5: Meera, an editor, shares it with Kabir", "<b>Why:</b> <code>201</code>: one tuple and one notice."),
    ("06-kabir-after-the-share", "Case 6: Kabir again", "<b>Why:</b> viewer now."),
    ("07-a-viewer-tries-to-share", "Case 7: Asha, a viewer, tries to share", "<b>Why:</b> <code>403</code>: she may know it exists, not pass it on."),
    ("08-asha-after-leaving-the-team", "Case 8: Asha after leaving the design team", "<b>Why:</b> one tuple deleted; the next request already says <code>404</code>."),
]) + """
<h2>The notice written with the share</h2>
""" + code(read("docs/captures/notices.txt").rstrip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Owner, editor, viewer", "The strongest relation wins", "<code>accessComesFromTheStrongestRelation</code>"],
    ["Folders in folders, teams in teams", "Inherited", "<code>accessFlowsThroughFoldersAndTeamsInTeams</code>"],
    ["An editor shares with a user", "<code>201</code>, the user can open it, a notice is written", "<code>anEditorSharesWithAUserAndTheyCanOpenIt</code>"],
    ["A share with a team", "Every member, nested ones too", "<code>sharingWithATeamReachesEveryMember</code>"],
    ["Shared with me", "What you can open and do not own", "<code>sharedWithMeListsWhatICanOpenButDoNotOwn</code>"],
    ["Unknown document; bad shares", "<code>404</code>; <code>400</code>", "<code>unknownDocumentsAre404AndBadSharesAre400</code>"],
    ["No or wrong credentials", "<code>401</code>", "<code>noOrWrongCredentialsAre401</code>"],
    ["A viewer shares; a stranger shares themselves in", "<code>403</code>; <code>404</code>", "<code>aViewerCannotShareAndAStrangerCannotEvenSee</code>"],
    ["Another user's or team's access", "Not yours: <code>404</code>", "<code>oneUsersAccessIsNotAnothersAndTeamsDoNotLeakAcross</code>"],
    ["Paths and methods with no rule", "<code>403</code>", "<code>pathsAndMethodsWithoutARuleAreRefused</code>"],
    ["A folder inside itself", "The check still ends, with the right answers", "<code>aFolderLoopDoesNotHangTheCheck</code>"],
    ["Odd ids and subjects", "<code>400</code> or <code>404</code>, never an error", "<code>oddIdsAndSubjectsAre400Or404NeverAnError</code>"],
    ["Tuples written by plain SQL", "Refused by named constraints", "<code>tupleRulesHoldWithoutJava</code>"],
    ["A share whose notice fails", "Nothing granted", "<code>aShareWhoseNoticeFailsGrantsNothing</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Copying permissions onto each document, so removing someone from a team leaves old access behind.</p>
<ul>
<li><strong>Left the team, kept the documents.</strong> The old copied rows still say Asha may read. With tuples, one row out of the team and her next request is <code>404</code>, for both documents and her shared list.</li>
<li><strong>Added later, shared never.</strong> A document put into the folder after the share had no copied rows. With tuples the team can open it.</li>
<li><strong>Joined later.</strong> A new team member gets the team's documents, and a document shared with the team follows whoever is in it.</li>
</ul>
<p>While building, each part was undone once: no teams inside teams turned 2 tests red; no folder inheritance 7; viewers allowed to share 1; the share without its transaction 1; owned documents listed as shared 1; no check for unknown users and teams 1; <code>denyAll</code> replaced by <code>authenticated</code> 1, after a test for paths without a rule was added.</p>
</div>
""" + code(read(T + "CopiedPermissionsTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "Permissions.java", dwn("The whole permission model: two recursive queries over the tuples.",
        "Who you are (you and your teams, through teams in teams) and what this is (the document and its folders); the strongest relation between them. The reverse walk lists what is shared with you.",
        "Access that outlives the relationship it came from, and thirty slightly different checks.",
        "<ul><li><code>max()</code> over no rows is <code>null</code>, and <code>JdbcClient</code>'s <code>single()</code> refuses a null value (\"Result value is null but no null value expected\"): the query uses <code>coalesce(..., 0)</code>. Found while building.</li><li><code>UNION</code> (not <code>UNION ALL</code>) drops rows already seen, so a folder placed inside itself cannot make the query run forever.</li></ul>")),
    (J + "Documents.java", dwn("Open and share.",
        "No relation is <code>404</code>; viewers cannot share; one tuple per share (a team share is one row for the whole team) plus a notice, in one transaction.",
        "Team shares copied into member rows, or a viewer handing a document on.")),
    (J + "DocumentController.java", dwn("The three endpoints.",
        "Subjects and relations checked by shape before anything else.",
        "Strings like <code>team:design#member</code> or SQL in a subject.")),
    (J + "SecurityConfig.java", "<p>HTTP Basic with demo users; the three paths need a sign-in; everything else refused.</p>"),
    (J + "ProblemResponses.java", "<p>401 with a Basic challenge and 403 in the same problem JSON as every other error.</p>"),
    (M + "V1__documents_and_relation_tuples.sql", dwn("Documents, tuples, notices.",
        "Which relations each object type has, what a subject may be, one parent and one owner at most.",
        "A tuple that means nothing (a team with an owner, a parent that is a user) written by any tool.")),
    (M + "V2__demo_workspace.sql", "<p>The demo workspace: four documents, two folders, two teams, twelve tuples.</p>"),
    ("src/main/resources/application.yaml", "<p>The database connection.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
    (J + "SharingApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/079-document-sharing-with-relationship-based-permissions/
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
<p>Take Neha out of brand-leads and ask again:</p>
""" + code("""curl -s -o /dev/null -w '%{http_code}\\n' -u neha:neha-demo-pass http://localhost:8080/docs/d-guidelines
docker compose exec postgres psql -U taskloom -d taskloom -c "DELETE FROM relation_tuples WHERE object_id = 'brand-leads' AND subject_id = 'neha'"
curl -s -o /dev/null -w '%{http_code}\\n' -u neha:neha-demo-pass http://localhost:8080/docs/d-guidelines""", "bash") + """
<p>200, then 404. Nothing else changed: no document row, no cache.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>Result value is null but no null value expected</code>", "<code>single()</code> on an aggregate over no rows.", "<code>coalesce</code> in SQL, or <code>optional()</code>. Found while building this station."],
    ["<code>relation_tuples_subject</code> violated", "A team written as a plain subject, without <code>#member</code>.", "Teams are subjects only as \"every member of\"."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">The permission model first, then the endpoints and the database behind them.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>SharingContractTest</code> ({cnt('SharingContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>CopiedPermissionsTrapTest</code> ({cnt('CopiedPermissionsTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>SharingDatabaseTest</code> ({cnt('SharingDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, one user accessing another user's data, malicious input", f"<code>SharingSecurityTest</code> ({cnt('SharingSecurityTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">Before each test the demo workspace is rebuilt from the V2 migration file itself, so every test starts from the tuples shown in the API tab.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "CopiedPermissionsTrapTest.java", "<p>Written first: copied rows that outlive the team, miss new documents; tuples that follow the team.</p>"),
    (T + "SharingSecurityTest.java", "<p>401, viewers and strangers, access that is not yours, paths with no rule, a folder loop, odd input.</p>"),
    (T + "SharingDatabaseTest.java", "<p>Every named tuple rule with plain SQL; a share whose notice fails grants nothing.</p>"),
    (T + "SharingContractTest.java", "<p>Open, share, shared with me, through HTTP.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the demo workspace from V2 before each test, request helpers, the team admin's one statement.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/taskloom/sharing/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=UnshareChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Take a share back", "Beginner-friendly", 20,
    "<code>DELETE /docs/{id}/shares/{subject}</code> removes that subject's viewer and editor tuples on the document (<code>204</code>). Editors and owners only; the owner tuple stays.",
    "both tests in <code>UnshareChallengeTest</code> pass.",
    ["One <code>DELETE</code> with <code>relation IN ('viewer', 'editor')</code>.", "The same 404 and 403 as sharing."],
    "challenge/UnshareChallengeTest.java", ["challenge/solution/Documents.java", "challenge/solution/DocumentController.java", "challenge/solution/SecurityConfig.java"]) + challenge(2, "Who has access?", "Go deeper", 40,
    "<code>GET /docs/{id}/access</code>: every user who can open the document, with their strongest access, through folders and teams in teams, for editors and owners.",
    "both tests in <code>WhoHasAccessChallengeTest</code> pass.",
    ["Walk up from the document to its folders, collect the subjects of their grants, then walk down from teams to their members.",
     "Zanzibar calls this expand; it is the check run backwards."],
    "challenge/WhoHasAccessChallengeTest.java", ["challenge/solution/Permissions.java", "challenge/solution/Documents.java", "challenge/solution/DocumentController.java", "challenge/solution/SecurityConfig.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Your own tables, or a permission service?</h2>
<p>Write the same model in OpenFGA's or SpiceDB's schema language. What would move out of PostgreSQL, what new failure would the app have (the permission service is down), and how do you keep a share and the check that follows it consistent (Zanzibar's zookies, SpiceDB's ZedTokens)? At what size would you switch?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: copied rows that outlive their reason.</li>
<li>One tuple table, with the allowed relations per object type as constraints.</li>
<li>One recursive check: who you are, what this is, the strongest link.</li>
<li>Shares write one tuple, never a copy per member.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Tuples in PostgreSQL, recursive CTE per check", "A walk per request; fine for shallow trees.", '<span class="pill ok">Chosen</span>'],
    ["Copy access rows onto each document", "Stale the moment a team or folder changes.", '<span class="pill bad">The trap</span>'],
    ["Expand team shares into member rows at write time", "Fast reads; misses later members and teams in teams.", '<span class="pill bad">The review version</span>'],
    ["OpenFGA or SpiceDB", "A separate service and its consistency tokens; built-in expand, caching, audit.", '<span class="pill warn">At scale, or many products</span>'],
    ["PostgreSQL row-level security on top", "Rules enforced for every query; harder to read.", '<span class="pill warn">Defence in depth</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>relation_tuples_relation_for_type</code>", "CHECK", "Teams have members; folders viewers, editors, a parent; documents also an owner."],
    ["<code>relation_tuples_subject</code>", "CHECK", "A parent is a folder; any other subject is a user or every member of a team."],
    ["<code>relation_tuples_one_parent</code>, <code>_one_owner</code>", "Partial UNIQUE indexes", "A tree, not a graph of parents; one owner."],
    ["<code>relation_tuples_by_subject</code>", "Index", "The walk from a user to their teams."]]) + """
<p><strong>Transaction boundary:</strong> a share (its tuple and its notice) is one transaction. Checks are single statements.</p>
""" + code(read(M + "V1__documents_and_relation_tuples.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Depth</dt><dd>Each level of folders or teams is another step of the walk. Measure checks on the deepest real tree before promising response times.</dd>
<dt>Caching</dt><dd>Caching a check brings back the stale-access problem. Zanzibar answers this with consistency tokens; without them, keep caches very short or skip them.</dd>
<dt>Audit</dt><dd>Tuples are the permission state: log every write to them (who shared what with whom).</dd>
<dt>Sources</dt><dd>\"Zanzibar: Google's Consistent, Global Authorization System\", USENIX ATC 2019. OpenFGA is a CNCF project; SpiceDB is open source from AuthZed.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is relationship-based access control?", "Access derived from relationships (member of, parent of, viewer of) at check time, instead of permissions stored per resource."),
    ("Why do copied permissions go stale?", "They record the outcome, not the reason. When the reason (team membership, folder) changes, nothing updates the copies."),
    ("What is a userset?", "A set of subjects defined by a relation, such as every member of a team, used as one subject in a tuple."),
    ("How does the recursive query end?", "UNION drops rows already produced, so each object or team is visited once, even if the data has a cycle."),
    ("When would you move to OpenFGA or SpiceDB?", "When several services need the same checks, trees get deep, or you need expand, caching with consistency and audit out of the box."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Model", "Tuples with teams and folders.", "Teams in teams; constraints per object type."],
    ["Checks", "One recursive query.", "Safe against cycles; strongest relation wins."],
    ["Change", "Removing a member removes access.", "No copies anywhere, including team shares."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("Team shares copied into member rows",
     "\"Checks need no walk through teams\" brings the incident back for document shares: whoever leaves the team keeps the document, whoever joins never gets it, and teams inside the team are skipped altogether.",
     "<code>aDocumentSharedWithATeamFollowsTheTeamAfterwards</code> and <code>sharingWithATeamReachesEveryMember</code> (Neha is in a team inside the team) fail."),
    ("Viewers may share",
     "\"As with a link\": a viewer can now give anyone, or a whole team, the same access, and an editor share needs only viewer rights.",
     "<code>aViewerCannotShareAndAStrangerCannotEvenSee</code> fails."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate speeds up checks: a share with a team is written as one row per current member, so \"checks need no walk through teams\". Viewers may also pass documents on, \"as with a link\". Read the file and list every problem before opening the findings.</p>
<p class="path">review/Documents.java</p>
""" + code(read("review/Documents.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed file copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">Right after the share, everything looks correct. The flaw appears only when the team changes, which is why the trap tests change teams.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
