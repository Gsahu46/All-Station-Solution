"""Station 109 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 109,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring Security (HTTP Basic) · JdbcClient · PostgreSQL 17 row-level security · Flyway · Testcontainers",
    "simulation": "The companies, people and leads are demo data. Sign-in is a fixed list of demo users; a real identity provider would put the tenant in a signed token.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (PostgreSQL for the app, Testcontainers for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/taskloom/crm/"
T = "src/test/java/com/taskloom/crm/"
M = "src/main/resources/db/migration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Tenant", "One customer company using the shared software, with its own data.", "One flat in an apartment block.", "<code>zestful</code>, <code>brightpath</code>"),
    ("Multi-tenancy", "Many customers on one system, each seeing only their own data.", "One building, many locked flats.", "shared tables with a <code>tenant_id</code>"),
    ("Tenant from the token", "Which company you are is decided by your sign-in, never by what the request says.", "Your key opens your flat; saying a flat number does not.", "<code>SecurityConfig.tenant</code>"),
    ("Row-level security", "A rule in the database that hides other tenants' rows from every query.", "A lift that only stops at your floor.", "<code>leads_tenant_isolation</code>"),
    ("Defence in depth", "Two independent guards, so one mistake is not a leak.", "A locked flat in a building with a guard.", "WHERE clause + policy"),
    ("Isolation test", "A test that signs in as one tenant and tries to reach another's data.", "Trying your key in the neighbour's door.", "<code>LeadSecurityTest</code>"),
]
STORY = [
    ("Many companies, one CRM", "Taskloom's CRM keeps sales leads for hundreds of small companies in the same tables, each row marked with its company."),
    ("One forgotten WHERE", "A new \"find lead by email\" lookup forgot the company filter. A salesperson at one company saw another company's notes on a shared contact. Elsewhere, an endpoint read the company from the request body: changing one word put a lead into someone else's CRM."),
    ("The fix", "The company comes from the sign-in only. Every query filters by it, and underneath, the database itself filters by it: a query that forgets returns nothing from anyone else."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Isolation that depends on every developer remembering every WHERE clause will fail once. Put a second guard where nobody can forget it.</p>

<h2>What are we building?</h2>
<p>A leads API for many companies at once, where each company sees and writes only its own leads, enforced in the code and in the database.</p>

<h2>An everyday analogy</h2>
<p>An apartment block: your key decides which flat you enter, not the number you say at the gate; and even if someone leaves a door open, the lift only stops at your floor.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Sign in</strong>: the user's company is part of their account.</li>
<li><strong>Open a tenant transaction</strong>: the database is told the company, and switches to the application's limited role.</li>
<li><strong>Query</strong>: every query filters by the company.</li>
<li><strong>Underneath</strong>: the database's policy filters again; writes for another company are refused.</li>
</ol>

<details class="qa check"><summary>Check yourself: if the policy filters anyway, why keep the WHERE clause?</summary><p>Two guards: the WHERE clause is what developers read and indexes use; the policy catches the day one is missing. Remove either and one mistake is no longer harmless.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No identity provider.</strong> Demo users; the tenant would be a claim in a signed token.</li>
<li><strong>No admin view across companies.</strong> That is a separate, audited tool, not a parameter.</li>
<li><strong>One tenancy model.</strong> Shared tables; schema or database per tenant are compared in Design.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Taskloom</strong> (a fictional SaaS company): a missing WHERE clause in its CRM showed one customer company's leads to another.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> a signed-in user, <b>then</b> <code>GET /leads</code> lists only their company's leads, filtered by status and text.</li>
<li><b>Given</b> a lead id of another company, <b>then</b> <code>404</code>, the same as a lead that does not exist.</li>
<li><b>Given</b> <code>POST /leads</code> from a salesperson, <b>then</b> <code>201</code> in their company; an email already a lead of theirs, <code>409</code>; the same email at another company is fine.</li>
<li><b>Given</b> a company named in the body or the query string, <b>then</b> it is ignored.</li>
<li><b>Given</b> no sign-in, a viewer writing, or bad input, <b>then</b> <code>401</code>, <code>403</code>, <code>400</code>.</li>
<li><b>Given</b> any SQL in the application's role, <b>then</b> only the transaction's company's rows can be read or written.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>The tenant comes from the sign-in only.</li>
<li>Every query filters by tenant, and a database policy filters underneath.</li>
<li>The tenant setting ends with its transaction: a pooled connection never carries it on.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Compare tenancy models: shared tables, schema per tenant, database per tenant.</li>
<li>Take the tenant from the identity, never the request.</li>
<li>Use PostgreSQL row-level security with a non-owner role.</li>
<li>Write isolation tests that try to cross tenants, by API and by SQL.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app and its PostgreSQL, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Who", "Purpose"], [
    ["<code>GET</code>", "<code>/leads?status=&amp;q=</code>", "sales, viewer", "The company's leads, at most 50, newest first; <code>q</code> matches name, company or email as plain text."],
    ["<code>GET</code>", "<code>/leads/{id}</code>", "sales, viewer", "One of the company's leads."],
    ["<code>POST</code>", "<code>/leads</code>", "sales", "<code>{name, email, company?, status?}</code>."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span> / <span class="pill ok">201</span>', "Listed / created"],
    ['<span class="pill warn">400</span>', "Bad email, unknown status, search text too long"],
    ['<span class="pill warn">401</span> / <span class="pill warn">403</span>', "Not signed in / a viewer writing"],
    ['<span class="pill warn">404</span>', "No such lead in your company (whether or not it exists elsewhere)"],
    ['<span class="pill warn">409</span>', "Your company already has a lead with this email"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. Ananya and Kabir work at Zestful Foods, Farhan at Brightpath Tutors. <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-zestfuls-leads", "Case 1: Ananya lists her leads", "<b>Why:</b> Zestful's two."),
    ("02-brightpaths-leads", "Case 2: Farhan lists his", "<b>Why:</b> Brightpath's two; Rahul Mehta is a lead of both, as two separate rows."),
    ("03-a-new-lead", "Case 3: Ananya adds a lead", "<b>Why:</b> <code>201</code>; the email lower-cased."),
    ("04-the-same-email-again", "Case 4: the same email again", "<b>Why:</b> <code>409</code>."),
    ("05-the-same-email-at-another-company", "Case 5: Farhan adds the same person", "<b>Why:</b> <code>201</code>: unique per company, not across."),
    ("06-a-tenant-in-the-body", "Case 6: a body naming Brightpath", "<b>Why:</b> the body's tenant is not read: the lead is Zestful's (it appears among Zestful's rows in the psql listing below)."),
    ("07-a-tenant-in-the-query", "Case 7: <code>?tenant=brightpath</code>", "<b>Why:</b> ignored: Zestful's Rahul only."),
    ("08-another-companys-lead-by-id", "Case 8: Brightpath's lead 3, by id", "<b>Why:</b> <code>404</code>."),
    ("09-a-viewer-tries-to-create", "Case 9: Kabir, a viewer, adds a lead", "<b>Why:</b> <code>403</code>."),
    ("10-no-sign-in", "Case 10: no sign-in", "<b>Why:</b> <code>401</code>."),
    ("11-a-percent-sign-is-text", "Case 11: searching for %", "<b>Why:</b> a literal %, not \"anything\": nothing found."),
    ("12-a-bad-email", "Case 12: a bad email", "<b>Why:</b> <code>400</code>."),
]) + """
<h2>The policy, in psql</h2>
<p class="muted">The same database, as the application's role, with queries that have no WHERE at all:</p>
""" + code(read("docs/captures/policy.txt").strip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["The old code: tenant from the body; a lookup without tenant", "A lead planted at Brightpath; both companies' rows returned", "<code>theOldCodeTrustedTheBodysTenantAndForgotTheTenantInOneQuery</code>"],
    ["The API: the same body, a tenant in the query, the same forgetful query", "Zestful's lead; Zestful's rows only", "<code>theApiTakesTheTenantFromTheSignInAndTheDatabaseFiltersWhatACodeForgets</code>"],
    ["Listing and filtering", "Own leads only", "<code>aTenantListsAndFiltersItsOwnLeads</code>"],
    ["Create; duplicate; same email elsewhere", "<code>201</code>; <code>409</code>; <code>201</code>", "<code>aLeadIsCreatedOnceAnEmailPerTenant</code>"],
    ["Bad input; unknown id", "<code>400</code>; <code>404</code>", "<code>badInputIs400AndAnUnknownLeadIs404</code>"],
    ["No sign-in; a viewer writing", "<code>401</code>; <code>403</code>", "<code>noSignInIs401AndAViewerCannotCreate</code>"],
    ["Another company's lead by id or search", "<code>404</code>; not listed", "<code>anotherTenantsLeadIsNotFoundByIdOrBySearch</code>"],
    ["%, _, and SQL in the search text", "Plain text; nothing extra found", "<code>searchTextIsTextNotSqlOrAPattern</code>"],
    ["SQL with no WHERE, as the app's role", "Only the transaction's tenant; no tenant, no rows; other tenant's writes refused", "<code>thePolicyShowsAndWritesOnlyTheTransactionsTenant</code>"],
    ["Plain SQL against the rules", "Named constraints", "<code>theRulesAreNamedConstraints</code>"],
    ["A failed write; pooled connections", "Rolled back; the tenant does not stay on the connection", "<code>theTenantEndsWithItsTransactionAndAFailedWriteLeavesNothing</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Taking the tenant id from the request body, or forgetting it in one query.</p>
<ul>
<li><strong>The old way.</strong> The repository took the tenant it was given by the request, and one lookup by email had no tenant at all. Ananya's request plants a lead in Brightpath's CRM, and the lookup returns both companies' rows for Rahul Mehta.</li>
<li><strong>The API.</strong> The same body lands in Zestful. A tenant in the query string is ignored. And the very same forgetful lookup, run inside Zestful's transaction, returns Zestful's row only: the policy filtered what the code forgot.</li>
</ul>
<p>While building, each part was undone once. Removing the WHERE clause alone turned <b>0</b> tests red: the policy still filtered every query, which is the point of a second guard, and also why it was undone together with the role switch, which turned 6 red. Then: no role switch alone 2; no tenant setting 7; LIKE wildcards not escaped 1; emails not lower-cased 1; viewers allowed to write 1; a <code>?tenant=</code> parameter honoured 1.</p>
</div>
""" + code(read(T + "TenantLeakTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "LeadController.java", dwn("The endpoints.", "The tenant from the sign-in, every time; validation; email lower-cased with <code>Locale.ROOT</code>.", "A tenant chosen by the caller.")),
    (J + "Leads.java", dwn("The queries.", "Each says <code>WHERE tenant_id</code> and runs inside a tenant transaction; LIKE wildcards in search text are escaped.", "A lookup that forgets the tenant; a % that matches everything.")),
    (J + "TenantScope.java", dwn("The tenant transaction.", "<code>SET LOCAL ROLE crm_app</code> and <code>set_config('app.tenant', ..., true)</code>, then the work.", "A connection that bypasses the policy; a tenant left on a pooled connection.",
        "<ul><li>Superusers and table owners skip row-level security. The test database's user is a superuser, so the scope switches to <code>crm_app</code>: without that line, 2 tests go red (the policy test and the trap's forgetful query). Production connects as <code>crm_app</code> from the start.</li></ul>")),
    (J + "SecurityConfig.java", dwn("Users and tenants.", "Each user carries a <code>TENANT_</code> authority; roles decide reading and writing.", "A tenant from the request.",
        "<ul><li>Shortcut: a fixed list of demo users; with an identity provider, the tenant is a claim in the token.</li></ul>")),
    (M + "V1__tenants_and_leads.sql", dwn("Tables, role and policy.", "<code>tenant_id</code> on every lead, uniqueness per tenant, <code>crm_app</code> without DELETE, and <code>FORCE ROW LEVEL SECURITY</code> with USING and WITH CHECK.", "Any query, from any code, seeing another company.")),
    (M + "V2__demo_tenants.sql", "<p>Two companies and their leads, written with each tenant set: the policy applies to migrations too.</p>"),
    ("src/main/resources/application.yaml", "<p>The database.</p>"),
    ("compose.yaml", "<p>PostgreSQL 17 for running the app.</p>"),
]
tree = """stations/109-tenant-isolation-in-a-crm/
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
""" + code("""docker compose up -d --wait   # PostgreSQL 17 on localhost:5432
./mvnw spring-boot:run        # the API on http://localhost:8080
./mvnw test                   # all """ + str(N_TESTS) + """ tests; starts its own PostgreSQL container""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d --wait
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Ask the database directly, as the application's role, with and without a tenant:</p>
""" + code("""docker compose exec postgres psql -U crm -d crm -c "BEGIN; SET LOCAL ROLE crm_app; SELECT count(*) FROM leads; COMMIT;"
docker compose exec postgres psql -U crm -d crm -c "BEGIN; SET LOCAL ROLE crm_app; SELECT set_config('app.tenant','zestful',true); SELECT name FROM leads; COMMIT;\"""", "bash") + """
<p>0 rows, then Zestful's. As <code>crm</code> (the owner, a superuser) without <code>SET ROLE</code>, all four: the policy does not bind superusers, which is why the application must not be one.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Every list is empty", "<code>app.tenant</code> not set in the transaction, or set outside it.", "Run queries through <code>TenantScope</code>."],
    ["Another company's rows appear", "The connection is a superuser or the table owner, and the role was not switched.", "Connect as <code>crm_app</code>, or <code>SET LOCAL ROLE crm_app</code>; keep <code>FORCE ROW LEVEL SECURITY</code>."],
    ["<code>new row violates row-level security policy</code>", "A write for a tenant other than the transaction's.", "The tenant must come from the sign-in."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the database.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>LeadContractTest</code> ({cnt('LeadContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>TenantLeakTrapTest</code> ({cnt('TenantLeakTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Database", "Rollback and constraint tests against a real database", f"<code>LeadDatabaseTest</code> ({cnt('LeadDatabaseTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, another user's data, malicious input", f"<code>LeadSecurityTest</code> ({cnt('LeadSecurityTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">The database tests run plain SQL as <code>crm_app</code> with no WHERE at all, so they test the policy, not the Java filters. The tests' own connection is a superuser, which is how they set up and inspect every tenant's rows.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, PostgreSQL 17 in Testcontainers. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "TenantLeakTrapTest.java", "<p>Written first: the old repository and the API.</p>"),
    (T + "LeadContractTest.java", "<p>Listing, creating, bad input.</p>"),
    (T + "LeadSecurityTest.java", "<p>Sign-in, roles, other tenants, hostile search text.</p>"),
    (T + "LeadDatabaseTest.java", "<p>The policy and the constraints with plain SQL; a rollback.</p>"),
    (T + "ApiTest.java", "<p>Shared setup.</p>"),
    (T + "PostgresTestConfig.java", "<p>PostgreSQL 17 in Docker via Testcontainers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/taskloom/crm/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=LeadStatusChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Move a lead along", "Beginner-friendly", 20,
    "Add <code>PATCH /leads/{id} {status}</code> for salespeople: their company's lead only; another company's id is <code>404</code> and stays unchanged; a viewer gets <code>403</code>.",
    "both tests in <code>LeadStatusChallengeTest</code> pass.",
    ["<code>UPDATE ... WHERE tenant_id = ? AND id = ? RETURNING ...</code> inside <code>TenantScope</code>: no row means 404.",
     "The policy would also make another company's row invisible to the UPDATE: try it without the WHERE."],
    "challenge/LeadStatusChallengeTest.java", ["challenge/solution/LeadController.java", "challenge/solution/Leads.java", "challenge/solution/SecurityConfig.java"]) + challenge(2, "Notes that cannot cross", "Go deeper", 35,
    "Add notes: <code>POST /leads/{id}/notes {text}</code>. In a new table, with the database guaranteeing a note's tenant is its lead's tenant (<code>lead_notes_lead_of_same_tenant</code>) and the same row-level policy as leads.",
    "both tests in <code>LeadNotesChallengeTest</code> pass.",
    ["A foreign key on two columns, <code>(lead_id, tenant_id)</code>, needs a UNIQUE on <code>leads (id, tenant_id)</code>.",
     "New tables need their own GRANTs, ENABLE and FORCE, and policy: nothing is inherited.",
     "A migration of its own: <code>V3__lead_notes.sql</code>."],
    "challenge/LeadNotesChallengeTest.java", ["challenge/solution/V3__lead_notes.sql", "challenge/solution/Leads.java", "challenge/solution/LeadController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>\"We want our own database\"</h2>
<p>A large customer asks for its data in a separate database, in a region of its choice. Compare shared tables (this station), a schema per tenant and a database per tenant for this customer and for the hundreds of small ones: isolation, migrations, backups and restores of one tenant, cost, and how the application picks the right connection. Which would you offer, and at what price point?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the old repository's two mistakes.</li>
<li>Take the tenant from the sign-in; drop it from every request shape.</li>
<li>Filter every query; add the policy, FORCE'd, with a non-owner role.</li>
<li>Test the policy with SQL that has no WHERE.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Model", "Isolation", "Cost and effort", "Verdict"], [
    ["Shared tables + tenant column + row-level security", "Good, with two guards", "Cheapest; one schema to migrate", '<span class="pill ok">Chosen</span>'],
    ["Shared tables + tenant column only", "One forgotten WHERE from a leak", "Cheapest", '<span class="pill bad">The trap</span>'],
    ["Schema per tenant", "Strong; search_path must be right", "Migrations per schema; hundreds of schemas", '<span class="pill warn">Mid-size customers</span>'],
    ["Database per tenant", "Strongest; separate backups and regions", "Most expensive; connection per tenant", '<span class="pill warn">Large customers</span>'],
    ["Tenant from the request", "None", "None", '<span class="pill bad">Never</span>']]) + """
<h2>Database design</h2>
""" + table(["Object", "What", "Why"], [
    ["<code>leads_tenant_isolation</code>", "Policy: USING and WITH CHECK <code>tenant_id = current_setting('app.tenant', true)</code>", "Reads and writes of the transaction's tenant only; no setting, no rows."],
    ["<code>FORCE ROW LEVEL SECURITY</code>", "The policy binds the table owner too", "Only superusers and BYPASSRLS roles skip it."],
    ["<code>crm_app</code>", "SELECT, INSERT, UPDATE; no DELETE", "The application cannot delete leads at all."],
    ["<code>leads_email_unique_per_tenant</code>", "UNIQUE (tenant_id, email)", "Once per company, not across companies."],
    ["<code>leads_status</code>, <code>tenants_id_format</code>", "CHECKs", "Known states; clean tenant ids."]]) + """
<p><strong>Transaction boundaries:</strong> every request's database work is one transaction that starts with the role and the tenant (both LOCAL), so neither outlives it.</p>
""" + code(read(M + "V1__tenants_and_leads.sql"), "sql")

# ---------- Level 3: Production ----------
prod = belongs(["14. Operations: metric, alert, rollback, runbook, failure drill", "15. Real-world considerations"],
               "What changes when this runs for real.") + """
<h2>Real-world considerations</h2>
<dl class="facts">
<dt>Connection role</dt><dd>Connect as <code>crm_app</code>; run migrations as the owner. Never give the application role BYPASSRLS.</dd>
<dt>Support access</dt><dd>When staff must see a customer's data, use a separate tool that sets the tenant from an approved, logged support ticket, never a parameter on the customer API.</dd>
<dt>Every new table</dt><dd>Needs its tenant column, its policy and its isolation test. A check in CI that lists tables without a policy catches the one that was forgotten.</dd>
<dt>Caches and search indexes</dt><dd>Anything outside the database (caches, search, exports, logs) needs the tenant in its key too; the policy does not reach there.</dd>
<dt>Performance</dt><dd>The policy adds a condition the planner uses with <code>leads_by_tenant</code>; check plans on the largest tenant.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Where should the tenant id come from?", "From the authenticated identity (a claim in the token, or the user's account), never from the body, path or query."),
    ("What is row-level security in PostgreSQL?", "Policies on a table that add a condition to every query and write; with FORCE, they bind the owner too. Superusers and BYPASSRLS roles skip them."),
    ("How do you pass the tenant to the database safely with a pool?", "SET LOCAL / set_config(..., true) inside the transaction, so it ends with the transaction."),
    ("Shared tables, schema per tenant or database per tenant?", "Shared tables for many small tenants; schemas or databases where isolation, regions or per-tenant restores matter enough to pay for."),
    ("How do you test isolation?", "Sign in as one tenant and try every way to reach another's data, and run SQL without WHERE as the app role."),
    ("Why return 404, not 403, for another tenant's id?", "403 confirms the id exists; 404 tells nothing."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Tenant source", "From the sign-in.", "No request field can name a tenant, and a test proves it."],
    ["Isolation", "WHERE on every query.", "A FORCE'd policy under it, a non-owner role, and SQL tests without WHERE."],
    ["Tenancy models", "Knows shared tables.", "Can argue schema or database per tenant for a given customer."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("The policy switched off without anyone noticing",
     "\"Switching roles is not needed: every query already says WHERE tenant_id\": the connection is the owner's, which the policy does not bind, so the second guard is gone. Nothing fails today; the next forgotten WHERE is a leak again.",
     "<code>thePolicyShowsAndWritesOnlyTheTransactionsTenant</code> fails: as the owner, a write for Brightpath inside Zestful's transaction goes through."),
    ("A tenant from the query string",
     "\"Support staff look at customers' CRMs: ?tenant= lets them switch company\": so can every customer. Any salesperson can add <code>?tenant=</code> and read another company's leads.",
     "<code>theApiTakesTheTenantFromTheSignInAndTheDatabaseFiltersWhatACodeForgets</code> fails: <code>?tenant=brightpath</code> returns Brightpath's lead."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate \"simplifies\" the scope and adds a support feature: \"the WHERE clauses already isolate tenants, and support needs to switch companies\". Read both files and list every problem before opening the findings.</p>
<p class="path">review/TenantScope.java</p>
""" + code(read("review/TenantScope.java"), "java") + """
<p class="path">review/LeadController.java</p>
""" + code(read("review/LeadController.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">Every listing in the flawed version is still correct for every user who does not type <code>?tenant=</code>. That is what makes both mistakes easy to merge.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
