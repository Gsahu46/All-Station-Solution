"""Station 092 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 92,
    "stack": "Spring Boot 4.1.1 · Java 25 · multipart uploads streamed to disk · size limits · type from magic bytes · path traversal · Spring Security 7 (HTTP Basic)",
    "simulation": "The customers, the reviewer and the documents are demo data. Files are stored in a local folder standing for object storage; the list of documents is kept in memory. No KYC check is done on the documents.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/tijori/kyc/"
T = "src/test/java/com/tijori/kyc/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Multipart upload", "The way browsers and apps send files in an HTTP request, in parts.", "A parcel with a form and a box inside.", "<code>multipart/form-data</code>"),
    ("Size limit", "The largest upload accepted, enforced before the file is read.", "A post office scale with a maximum.", "5 MB (demo rule)"),
    ("Magic bytes", "The first bytes of a file, which say what it really is.", "Reading the label inside the box, not the sticker outside.", "<code>%PDF-</code>, PNG, JPEG"),
    ("Path traversal", "A file name with <code>../</code> that climbs out of the upload folder.", "A parcel addressed \"two doors down\".", "<code>../../etc/passwd</code>"),
    ("Streaming", "Copying a file piece by piece, never holding it whole in memory.", "Passing buckets along a line.", "8 KB at a time"),
    ("KYC", "Know Your Customer: proving who a customer is with documents.", "Showing ID at a bank.", "PAN, passport, ..."),
]
STORY = [
    ("A 2 GB PAN card", "Someone uploaded a 2 GB file as a PAN card. The old code read every upload into memory with getBytes(): the server ran out of memory and stopped for everyone."),
    ("A file called ../../etc/passwd", "Another upload was named ../../etc/passwd. The old code saved it under the name the client sent, so it was written outside the upload folder. A program sent with Content-Type: application/pdf was stored as a \"PDF\"."),
    ("The fix", "The server refuses anything above 5 MB before reading it, copies files in small pieces, names each file itself, and decides the type from the file's first bytes."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Everything about an upload comes from the client: its size, its name and its type. Limit the first, ignore the second, check the third yourself.</p>

<h2>What are we building?</h2>
<p>Customers upload KYC documents (PDF, PNG or JPEG, up to 5 MB) and list their own; a reviewer can list anyone's.</p>

<h2>An everyday analogy</h2>
<p>A bank's document counter weighs each envelope first, gives it its own reference number instead of trusting what is written on it, and opens it to check it really is a passport copy.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Refuse big uploads</strong> before reading them: the server's multipart limit answers <code>413</code>.</li>
<li><strong>Read the first bytes</strong>: PDF, PNG or JPEG, or <code>415</code>.</li>
<li><strong>Stream</strong> the file to a name the server chooses, counting and hashing on the way.</li>
<li><strong>Record</strong> the document with its real type, size, SHA-256 and a cleaned-up display name.</li>
</ol>

<details class="qa check"><summary>Check yourself: a file named photo.png arrives with Content-Type: image/png, but starts with MZ. What is it?</summary><p>A Windows program. Name and header are the sender's claim; the first bytes are the file. The upload is refused with <code>415</code>: <code>theApiDecidesTheTypeFromTheBytes</code>.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No virus scanning.</strong> Checking the type is not checking for malware; real systems scan uploads too.</li>
<li><strong>No object storage.</strong> A local folder stands for S3 or similar.</li>
<li><strong>No document review.</strong> Nobody checks whether the PAN card is real.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Tijori</strong> (a fictional wallet app): a 2 GB \"PAN card\" upload took the server down; a file named <code>../../etc/passwd</code> was accepted.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo users: customers asha (1) and rohan (2), reviewer kavya; password <code>name-demo-pass</code>. Demo rules: at most 5 MB; PDF, PNG or JPEG; types PAN, PASSPORT, DRIVING_LICENCE, VOTER_ID.</p>
<ol class="gwt">
<li><b>Given</b> a PDF, PNG or JPEG up to 5 MB, <b>then</b> <code>201</code> with its detected type, size and SHA-256.</li>
<li><b>Given</b> more than 5 MB, <b>then</b> <code>413</code> before the file is read; nothing stored.</li>
<li><b>Given</b> any other content, whatever its name or header, <b>then</b> <code>415</code>.</li>
<li><b>Given</b> a file name with <code>../</code> or odd characters, <b>then</b> the file stays in its folder under a server-made name; the name is only a label.</li>
<li><b>Given</b> another customer's documents, <b>then</b> <code>403</code>; no sign-in, <code>401</code>; an unknown customer (reviewer), <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>No upload is held whole in memory.</li>
<li>No part of a storage path comes from the client.</li>
<li>The type is decided from the content.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Set multipart limits and see where they are enforced (the server, not MockMvc).</li>
<li>Stream uploads with limits of your own as a second line.</li>
<li>Detect file types by magic bytes.</li>
<li>Defend against path traversal by never using client names in paths.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/kyc/{customerId}/documents</code>", "Multipart: <code>type</code> and <code>file</code>. A customer uploads their own document."],
    ["<code>GET</code>", "<code>/kyc/{customerId}/documents</code>", "The customer's documents; a reviewer may list any customer's."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span> / <span class="pill ok">201</span>', "Listed / stored"],
    ['<span class="pill warn">400</span>', "An empty file, an unknown type, no file part"],
    ['<span class="pill warn">401</span>', "No sign-in, or a wrong password"],
    ['<span class="pill warn">403</span>', "Another customer's documents; a reviewer uploading"],
    ['<span class="pill warn">404</span>', "A reviewer asking for a customer that does not exist"],
    ['<span class="pill warn">413</span>', "Over 5 MB, refused before the file is read"],
    ['<span class="pill warn">415</span>', "Not a PDF, PNG or JPEG by its first bytes, whatever its name or Content-Type"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order. JSON bodies are indented for reading; <code>Date</code>, connection and standard security headers, and curl's <code>100 Continue</code>, are left out.</p>
""" + examples([
    ("01-asha-uploads-her-pan-card", "Case 1: Asha uploads her PAN card", "<b>Why:</b> a PDF by its first bytes; stored under a UUID; its SHA-256 recorded."),
    ("02-a-program-sent-as-a-pdf", "Case 2: a Windows program named pan.pdf, sent as application/pdf", "<b>Why:</b> it starts with <code>MZ</code>: <code>415</code>."),
    ("03-a-name-that-climbs-out-of-the-folder", "Case 3: the same PDF, named ../../etc/passwd", "<b>Why:</b> stored in Asha's folder under a UUID; <code>passwd</code> is only its label."),
    ("04-six-megabytes", "Case 4: 6 MB", "<b>Why:</b> the server's multipart limit: <code>413</code> before our code runs."),
    ("05-an-empty-file", "Case 5: an empty file", "<b>Why:</b> <code>400</code>."),
    ("06-asha-lists-her-documents", "Case 6: Asha lists her documents", "<b>Why:</b> the two she stored."),
    ("07-rohan-lists-ashas-documents", "Case 7: Rohan asks for Asha's", "<b>Why:</b> <code>403</code>."),
    ("08-no-sign-in", "Case 8: no sign-in", "<b>Why:</b> <code>401</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["A PDF", "Stored, its bytes exactly, with size and SHA-256", "<code>aDocumentIsStoredWithItsDetectedTypeSizeAndHash</code>"],
    ["A PNG sent as application/pdf; a JPEG with no extension", "Typed by its bytes", "<code>theTypeComesFromTheBytesNotTheHeader</code>"],
    ["Empty file, unknown type, no file part; unknown customer", "<code>400</code>; <code>404</code>", "<code>badUploadsAre400AndUnknownCustomersAre404</code>"],
    ["A name with ../", "Kept inside the folder under a UUID", "<code>theApiKeepsEveryFileInsideItsFolderUnderItsOwnName</code>"],
    ["A program sent as a PDF", "<code>415</code>, nothing stored", "<code>theApiDecidesTheTypeFromTheBytes</code>"],
    ["5 MB; 5 MB + 1 byte; 60 MB", "<code>201</code>; <code>413</code> from the server; <code>413</code> or a closed connection, nothing stored", "<code>upToFiveMegabytesIsAcceptedAndMoreIs413</code>"],
    ["A 64 MB stream past our own limit", "Stops after 5 MB and one piece", "<code>theCopyStopsAtTheLimitWithoutReadingTheRest</code>"],
    ["No sign-in, wrong password", "<code>401</code>", "<code>withoutAValidSignInIt401s</code>"],
    ["Another customer's documents", "<code>403</code>", "<code>oneCustomerCannotUploadForOrReadAnother</code>"],
    ["A reviewer", "Reads any customer, uploads for none", "<code>aReviewerReadsAnyCustomerButUploadsForNone</code>"],
    ["Backslashes, .htaccess, .., script tags, 300 characters, a NUL", "Harmless labels; every file inside the customer's folder", "<code>maliciousFileNamesBecomeHarmlessLabels</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Trusting the file name and Content-Type, and loading whole files into memory.</p>
<ul>
<li><strong>The old code's path.</strong> The test runs <code>uploads.resolve(file.getOriginalFilename())</code> with <code>../../escaped.pdf</code>: the file lands two folders up. The program inside is \"application/pdf\", by the client's word.</li>
<li><strong>The API.</strong> The same name: the file is in the customer's folder as a UUID, the name only a label. The same program: <code>415</code>.</li>
<li><strong>Memory.</strong> <code>getBytes()</code> holds an upload whole. Here the server's limit refuses big uploads first, parts above 64 KB go to a temporary file, and the copy is 8 KB at a time with a limit of its own.</li>
</ul>
<p>While building, each part was undone once: the client's name as the path turned 3 tests red; no byte check 3; no server limit 1; no copy limit 1; the full name kept as the label 2; leading dots kept 1; no owner check on upload 1; anyone may list 1; empty files accepted 1.</p>
</div>
""" + code(read(T + "TrustedFileNameTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "SecurityConfig.java", dwn("Who may call what.", "HTTP Basic; customers upload and list; reviewers list; everything else refused.", "Anyone uploading for anyone.")),
    (J + "KycController.java", dwn("The two endpoints.",
        "The signed-in customer must be the path's customer; the file part's stream is handed to the store; the client's name and type header are passed along only as a label.",
        "One customer's documents in another's hands.")),
    (J + "DocumentStore.java", dwn("Storing a document safely.",
        "Reads the first bytes to decide the type, streams to <code>root/customer/UUID</code> in 8 KB pieces with a 5 MB limit, hashes on the way, and cleans up the name for display.",
        "Path traversal, disguised programs and out-of-memory crashes.",
        "<ul><li><code>BufferedInputStream.mark/reset</code> lets the type check read the first bytes and give them back.</li><li>The copy's own limit is a second line: the server's multipart limit refuses big uploads first. Found while building: with the second line in place, removing the first changed no test until the size test checked where the 413 comes from.</li><li>The list of documents is in memory, marked with a <code>shortcut:</code> comment.</li></ul>")),
    (J + "ProblemResponses.java", "<p><code>401</code> and <code>403</code> in the same problem shape as other errors.</p>"),
    ("src/main/resources/application.yaml", dwn("The limits.", "<code>max-file-size: 5MB</code>, <code>max-request-size: 6MB</code>, parts above 64 KB to disk while they arrive, the storage folder.", "Unlimited uploads.")),
    (J + "KycApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/092-kyc-document-upload/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tijori/kyc/
│   ├── SecurityConfig.java   ├── KycController.java   ├── DocumentStore.java
│   └── ProblemResponses.java   └── KycApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/tijori/kyc/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs"""
codetab = belongs(["Set up and run: commands for Windows and macOS/Linux, troubleshooting", "Try it yourself",
                   "10. Complete working code, in the order a request travels", "11. Code explanation"],
                  "Level 2. Every command here was run and gave the results shown.") + """
<h2>Set up and run</h2>
""" + table(["You need", "Version", "Check with"], [
    ["JDK", "25 (recommended). JDK 21 also works, see below", "<code>java -version</code>"],
    ["Maven", "Not needed: the project ships the Maven wrapper", ""]]) + """
<p><strong>macOS / Linux</strong></p>
""" + code("""./mvnw spring-boot:run      # the API on http://localhost:8080; files in a tijori-kyc folder under your temp folder
./mvnw test                 # all """ + str(N_TESTS) + """ tests""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code(""".\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Rename any program or zip file to <code>pan.pdf</code> and upload it as Asha:</p>
""" + code("""curl -u asha:asha-demo-pass -F type=PAN -F 'file=@pan.pdf;type=application/pdf' http://localhost:8080/kyc/1/documents""", "bash") + """
<p>It answers <code>415</code>, as in case 2 (which <code>docs/capture.sh</code> sends with a file starting <code>MZ</code>). A real PDF of up to 5 MB gives <code>201</code>.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Size limits work with curl but not in MockMvc tests", "MockMvc does not apply multipart limits; Tomcat does.", "Test sizes against a real port, as <code>UploadSizeTest</code> does."],
    ["A client sees a closed connection instead of 413", "Far over the limit, Tomcat answers and stops reading (2 MB more by default).", "Expected; clients that read early responses, like curl, see the 413."],
    ["<code>OutOfMemoryError</code> on uploads", "<code>getBytes()</code> or <code>readAllBytes()</code> on an upload.", "Stream it (<code>getInputStream()</code>), with a limit."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>KycContractTest</code> ({cnt('KycContractTest')}), <code>UploadSizeTest</code> ({cnt('UploadSizeTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>TrustedFileNameTrapTest</code> ({cnt('TrustedFileNameTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, one user accessing another user's data, malicious input", f"<code>KycSecurityTest</code> ({cnt('KycSecurityTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted"><code>UploadSizeTest</code> starts the app on a real port, because MockMvc never applies multipart limits. Its 60 MB case accepts either a <code>413</code> or a closed connection, and checks that nothing was stored: Tomcat closes the connection when an upload is far over the limit, and Java's HttpClient, still sending, saw the close where curl reads the <code>413</code>. Found while building.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "TrustedFileNameTrapTest.java", "<p>Written first: the old path and header against the API.</p>"),
    (T + "UploadSizeTest.java", "<p>Sizes on a real port; the copy limit with a 64 MB stream made up as it is read.</p>"),
    (T + "KycContractTest.java", "<p>Uploads and lists through HTTP; bad uploads.</p>"),
    (T + "KycSecurityTest.java", "<p>401, 403, the reviewer, malicious file names.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: an empty storage folder before each test, sample files by their first bytes, request helpers.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/tijori/kyc/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=DownloadChallengeTest</code>.</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Download, safely", "Beginner-friendly", 25,
    "<code>GET /kyc/{customerId}/documents/{documentId}/content</code>: the file with its detected type, as an attachment with its cleaned-up name. Owner and reviewers only; unknown documents <code>404</code>.",
    "both tests in <code>DownloadChallengeTest</code> pass.",
    ["Find the document by id in the customer's list; never build a path from the id the client sends.",
     "<code>ContentDisposition.attachment().filename(...)</code>; Spring Security already sends <code>X-Content-Type-Options: nosniff</code>."],
    "challenge/DownloadChallengeTest.java", ["challenge/solution/KycController.java", "challenge/solution/DocumentStore.java", "challenge/solution/SecurityConfig.java"]) + challenge(2, "The same file twice", "Go deeper", 30,
    "An app retries an upload that timed out. The same bytes for the same customer and type are one document: <code>200</code> with the one already there. Other bytes or another type are new.",
    "both tests in <code>SameFileTwiceChallengeTest</code> pass.",
    ["The SHA-256 is known only after streaming: store, then compare, then delete the repeat.",
     "Two retries at once could both pass the check: guard the compare-and-add."],
    "challenge/SameFileTwiceChallengeTest.java", ["challenge/solution/DocumentStore.java", "challenge/solution/KycController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Straight to object storage, and scanning</h2>
<p>Move uploads off the API servers: the app asks for a pre-signed upload URL and sends the file straight to object storage. What limits can you still enforce (size, type, how long the URL works), and how does the API learn the upload finished? Where would a virus scan run, and what does a customer see while it does?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the old path and header.</li>
<li>Set the multipart limits; test them on a real port.</li>
<li>Read the first bytes for the type; stream to a server-made name with a limit and a hash.</li>
<li>Clean the client's name into a label; check owner and reviewer access.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Server limits, byte check, stream to a UUID name", "A small amount of careful code.", '<span class="pill ok">Chosen</span>'],
    ["getBytes() and the client's file name", "Out of memory; files written anywhere.", '<span class="pill bad">The trap</span>'],
    ["Path.of(name).getFileName()", "Blocks ../, but two uploads with one name overwrite each other, and odd names still reach the disk.", '<span class="pill bad">Review finding</span>'],
    ["Type by extension or Content-Type", "Trivial to fake.", '<span class="pill bad">Review finding</span>'],
    ["Pre-signed uploads to object storage", "No bytes through the API; checks move to after the upload.", '<span class="pill warn">At scale (challenge 3)</span>']]) + """
<h2>Database design</h2>
<p>This station has no database: the list of documents is in memory (a <code>shortcut:</code> comment says so) and files are in a folder. In production, a documents table would hold the same fields, with the storage key generated by the server and a unique (customer, type, sha256) for challenge 2.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Working Systems station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Limits at every hop</dt><dd>The load balancer, the server and the app should all limit body size; the smallest wins, so set them on purpose.</dd>
<dt>Scanning</dt><dd>Type checks are not virus checks. Scan KYC documents before anyone opens them.</dd>
<dt>Privacy</dt><dd>KYC documents are personal data: encrypt them at rest, log access, and delete them when the law and the purpose allow.</dd>
<dt>Temporary files</dt><dd>Multipart parts above the threshold sit in the server's temp folder while they arrive; give it space and clean-up.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("How do you stop a 2 GB upload?", "With the server's multipart limits, which refuse it before the application reads it, plus a limit while streaming as a second line. Test it on a real server: MockMvc does not apply them."),
    ("Why not trust the file name?", "It is text from the client: ../ climbs out of folders, and names collide. Store under a name you generate; keep the client's name only as a cleaned-up label."),
    ("How do you know a file's type?", "From its first bytes (magic numbers). The extension and the Content-Type header are the sender's claim."),
    ("What does streaming an upload mean?", "Copying it in small pieces from the request to storage, never holding it whole in memory."),
    ("What does nosniff do?", "X-Content-Type-Options: nosniff tells browsers not to guess a type from the content, so a download marked as a PDF is not run as something else."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Size", "A limit is set.", "Tested on a real port; a second limit while streaming."],
    ["Names and types", "No ../ in paths.", "No client text in paths at all; type from bytes."],
    ["Access", "401 and 403.", "Owner and reviewer rules, and a 404 that leaks nothing."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("The customer's file name as the stored name",
     "\"So support can find pan-card.pdf\": <code>getFileName()</code> drops <code>../</code>, but a second upload with the same name overwrites the first, the name <code>..</code> resolves to the folder itself, and every odd character reaches the disk.",
     "<code>theApiKeepsEveryFileInsideItsFolderUnderItsOwnName</code>, <code>aDocumentIsStoredWithItsDetectedTypeSizeAndHash</code> and <code>maliciousFileNamesBecomeHarmlessLabels</code> fail."),
    ("The type from the extension",
     "\"Checking the bytes is slow and fiddly\": a program named <code>pan.pdf</code> is now a PDF, an empty <code>.pdf</code> is accepted, a real PNG named <code>.pdf</code> is called a PDF, and a JPEG with no extension is refused.",
     "<code>theApiDecidesTheTypeFromTheBytes</code>, <code>theTypeComesFromTheBytesNotTheHeader</code> and <code>badUploadsAre400AndUnknownCustomersAre404</code> fail."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate makes stored files easier for support: each is saved under the customer's own file name (\"getFileName() takes care of ../\"), and the type comes from the extension instead of the first bytes. Read the file and list every problem before opening the findings.</p>
<p class="path">review/DocumentStore.java</p>
""" + code(read("review/DocumentStore.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed file copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">The size limits are untouched, and an honest customer uploading pan-card.pdf sees no difference. Every failure needs a name or a file someone chose to be odd.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
