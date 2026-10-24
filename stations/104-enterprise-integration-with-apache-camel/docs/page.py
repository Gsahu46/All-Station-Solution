"""Station 104 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 104,
    "stack": "Spring Boot 4.1.1 · Java 25 · Apache Camel 4.23 (SFTP, file, idempotent consumer, error handling) · RabbitMQ 4.1 · Spring AMQP · Testcontainers",
    "simulation": "The partner bank and its SFTP server are simulated (an SFTP server in Docker with demo files). Nothing is issued: valid lines become messages on a queue.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code) and Docker running (RabbitMQ and the bank's SFTP server for the app; Testcontainers starts its own for the tests). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/bimaly/integration/"
T = "src/test/java/com/bimaly/integration/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Integration route", "A pipeline that takes something from one system, changes or checks it, and hands it to another.", "A sorting office: letters in, sorted, out to the vans.", "SFTP → validate → queue"),
    ("Apache Camel", "A library of ready connectors (\"components\") and patterns for writing such routes in a few lines.", "A box of standard pipe fittings.", "<code>PolicyFileRoute</code>"),
    ("SFTP polling", "Looking in a remote folder every so often for new files.", "Checking the letterbox every half hour.", "every 30 s"),
    ("Idempotent consumer", "Remembers what it already handled and skips it if it comes again.", "Ticking off invoices already paid.", "two records on disk"),
    ("Dead-letter channel", "Where a message that can never be processed is put aside for a person.", "The \"return to sender\" tray.", "<code>data/dead-letter/</code>"),
    ("Redelivery", "Trying a failed step again after a short wait, in case the problem passes.", "Ringing back when the line was busy.", "3 times, 2 s apart"),
]
STORY = [
    ("Files at 2 am", "Partner banks sell Bimaly's insurance. Each night a bank drops a file of new policies on its SFTP server. 4,000 lines of home-made glue code read the files and put each policy on a queue for the issuance team."),
    ("Every policy twice", "One night the app was restarted for a deployment. The glue code had kept the list of files it had read in memory. After the restart it read the whole folder again, and the issuance team received every policy of the last month a second time."),
    ("The fix", "A short Camel route replaces the glue code. What has been processed is recorded on disk, by the file's content; a restart, or the bank sending the same file again, changes nothing. Bad lines are rejected with their reason, unreadable files are put aside, and a broker problem is retried."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Whatever must not happen twice needs a record that outlives the process. Memory is gone at the next restart.</p>

<h2>What are we building?</h2>
<p>A route that reads a bank's policy files from SFTP, checks them, and puts each valid policy on a queue exactly once per file, with a record of every run.</p>

<h2>An everyday analogy</h2>
<p>An accounts clerk who receives invoices by post. Each one is stamped \"entered\" in a ledger before it is paid. If the supplier posts the same invoice twice, or the clerk goes home and comes back, the ledger says it is done. A torn, unreadable invoice goes into a tray for the manager, not into the bin.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Poll</strong>: every 30 s, look in the bank's folder for files not seen before.</li>
<li><strong>Check the record</strong>: a file whose content was already processed is noted as a duplicate and skipped.</li>
<li><strong>Validate</strong>: a file that cannot be read goes to the dead-letter folder; a bad line is rejected with its reason.</li>
<li><strong>Send</strong>: valid lines go to the queue; the run is done only when the broker has confirmed every one.</li>
</ol>

<details class="qa check"><summary>Check yourself: why not just delete the file after reading it?</summary><p>It is the bank's folder, and the bank allows us to read only. Even where moving files is allowed, a crash between \"sent\" and \"moved\" leaves the file to be read again: you still need a record.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No real bank.</strong> An SFTP server in Docker with demo files.</li>
<li><strong>No policy issuance.</strong> That team reads the queue; here we only fill it.</li>
<li><strong>Not one server per bank.</strong> One bank, one folder; more banks are more routes of the same shape.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Bimaly</strong> (a fictional insurance broker) receives nightly policy files from partner banks on SFTP. The glue code that reads them is 4,000 lines long and sent a month of policies twice after a restart.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo rules: files named <code>BANK-YYYYMMDD.csv</code>, UTF-8, with the header <code>""" + "reference,customer_name,date_of_birth,product_code,sum_insured_paise" + """</code>, five columns without commas or quotes inside them, at most 10,000 lines; a poll every 30 s; a failed step tried 3 more times, 2 s apart.</p>
<ol class="gwt">
<li><b>Given</b> a good file, <b>then</b> every line is one message on <code>policy.requests</code> with the id <code>BANK:REFERENCE</code>, and the run is <code>DONE</code>.</li>
<li><b>Given</b> bad lines, <b>then</b> each is rejected with its line number and reason, and the others are sent.</li>
<li><b>Given</b> a file that cannot be read (name, header, encoding, empty), <b>then</b> nothing is sent, the file goes to the dead-letter folder as it arrived, and it is not tried again.</li>
<li><b>Given</b> the broker refuses, <b>then</b> the step is retried; if it still fails, the run is <code>FAILED</code> and the next poll tries the file again.</li>
<li><b>Given</b> a restart, or the same content uploaded again, <b>then</b> nothing is sent twice; a re-upload is recorded as <code>DUPLICATE</code>.</li>
<li><b>Given</b> <code>GET /integration/runs/{id}</code>, <b>then</b> <code>200</code> with what happened, <code>404</code> for an unknown run, <code>400</code> for a non-number.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>The bank's folder is read-only to us: files are never moved or deleted there.</li>
<li>What was processed is recorded on disk, by content.</li>
<li>Errors that will pass are retried; errors that never will are put aside at once.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Write a Camel route with the SFTP and file components.</li>
<li>Use an idempotent consumer with a store that survives restarts.</li>
<li>Separate retryable errors from dead letters with <code>onException</code>.</li>
<li>Publish to RabbitMQ with confirms and stable message ids.</li>
<li>Test a route against a real SFTP server and broker, including a restart.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, its RabbitMQ and the simulated bank's SFTP server, never typed by hand.") + """
<h2>The route and the endpoint</h2>
""" + table(["What", "Where", "Purpose"], [
    ["Route <code>policy-files</code>", "<code>sftp://koshbank@…/upload</code> → <code>policy.requests</code>", "Poll the bank's folder; validate; queue each valid line."],
    ["<code>GET</code>", "<code>/integration/runs/{id}</code>", "What happened to one file: status, lines, accepted, rejected lines with reasons, error."]]) + """
<h2>Run statuses</h2>
""" + table(["Status", "Meaning"], [
    ['<span class="pill ok">DONE</span>', "Valid lines sent and confirmed by the broker"],
    ['<span class="pill warn">DUPLICATE</span>', "The same content was already processed; nothing sent"],
    ['<span class="pill warn">FAILED</span>', "A step kept failing; the next poll tries the file again"],
    ['<span class="pill bad">DEAD_LETTERED</span>', "The file can never be processed as it is; a copy waits in the dead-letter folder"],
    ['<span class="pill">RUNNING</span>', "Being processed now"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured on """ + read("docs/captures/date.txt").strip() + """ by <code>docs/capture.sh</code>: three files uploaded at once (one poll takes them in name order), then the first again, then one while the broker refuses. <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-a-good-file", "Run 1: a good file", "<b>Why:</b> three lines, three messages."),
    ("02-a-file-with-bad-lines", "Run 2: a file with bad lines", "<b>Why:</b> one line sent; three rejected, each with its line number and reason."),
    ("03-a-file-that-cannot-be-read", "Run 3: a file with semicolons", "<b>Why:</b> the header is wrong: dead-lettered at once, no retry."),
]) + code(read("docs/captures/dead-letter.txt").strip(), "text") + """
<p class="muted">The queue after runs 1 to 3, read through RabbitMQ's management API without taking the messages off (message id, delivery mode 2 = persistent, body):</p>
""" + code(read("docs/captures/queue.txt").strip(), "text") + examples([
    ("04-the-same-file-again", "Run 4: the bank uploads run 1's file again", "<b>Why:</b> same content: a duplicate, nothing sent."),
    ("05-the-broker-refuses", "Run 5: the broker refuses every message", "<b>Why:</b> 3 retries 2 s apart, then <code>FAILED</code>; the file is not marked as processed."),
    ("06-the-next-poll-tries-again", "Run 6: the broker is back", "<b>Why:</b> the next poll picked the same file up again: <code>DONE</code>."),
    ("07-no-such-run", "No such run", "<b>Why:</b> <code>404</code>."),
    ("08-not-a-run-number", "Not a run number", "<b>Why:</b> <code>400</code>."),
]) + """
<h2>What the app remembers</h2>
<p class="muted">The two records on disk at the end of the capture:</p>
""" + code(read("docs/captures/records.txt").strip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["The old route, restarted", "The same file read again", "<code>theOldRouteReadsTheSameFileAgainAfterARestart</code>"],
    ["The app, restarted; then the same file under a new name", "Processed once; then <code>DUPLICATE</code>", "<code>theApiRemembersWhatItProcessedAcrossARestart</code>"],
    ["A good file", "<code>DONE</code>; one message per line, id <code>BANK:REFERENCE</code>, codes upper-cased", "<code>aFileIsCheckedAndItsValidLinesQueued</code>"],
    ["Missing column, future birth date, bad sum, repeated reference", "Rejected with line number and reason; the rest sent", "<code>badLinesAreRejectedWithTheirReasonAndTheOthersGoOn</code>"],
    ["Unknown run; not a number", "<code>404</code>; <code>400</code>", "<code>anUnknownRunIs404AndANonNumberIs400</code>"],
    ["The broker refuses", "Retried, <code>FAILED</code>, then <code>DONE</code> on a later poll", "<code>aBrokerThatRefusesIsRetriedThenTheFileIsTriedAgainOnTheNextPoll</code>"],
    ["A wrong header", "Dead-lettered once, as it arrived", "<code>aFileThatCanNeverBeReadGoesToTheDeadLetterFolderOnce</code>"],
    ["A wrong name; a header only", "Dead-lettered", "<code>aWrongFileNameOrAnEmptyFileIsDeadLetteredToo</code>"],
    ["The same file uploaded again, same or new name", "<code>DUPLICATE</code>; nothing sent", "<code>theSameFileUploadedAgainSendsNothingAndIsRecordedAsADuplicate</code>"],
    ["A corrected file with the same name", "Processed; unchanged lines sent again with the same ids", "<code>aCorrectedFileWithTheSameNameIsProcessed</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Processing the same file twice after a restart because nothing records what was already consumed.</p>
<ul>
<li><strong>The old way.</strong> The bank's folder is read-only, so the route uses <code>noop=true</code>, and Camel then remembers the files it read. In memory: within one run the file is read once; after a restart (a new Camel context) it is read again.</li>
<li><strong>The API.</strong> The app is started, processes the file, is stopped and started again: the file is not processed again. Then the bank uploads the same file under a new name: it is recorded as a duplicate, and the queue still holds only the first two messages.</li>
</ul>
<p>While building, each part was undone once: the downloaded-files record in memory turned 1 test red; the processed-files record in memory 1; no duplicate check 2; no dead-letter handling 2; every error handled (never retried) 1; no publisher confirms 1; no message ids 5; product codes not upper-cased 1; repeated references allowed 1; birth dates in the future allowed 1.</p>
</div>
""" + code(read(T + "FileRestartTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "PolicyFileRoute.java", dwn("The route.", "Polls the bank's folder, checks the record, validates, sends, and records the run. Two <code>onException</code> blocks: never-retry (dead letter) and retry-then-fail.", "4,000 lines of glue code; a file read twice; a broken file retried for ever.",
        "<ul><li><code>noop=true</code> because the folder is read-only; <code>sortBy=file:name</code> so a poll with several days' files takes them in date order.</li><li><code>handled(false)</code> on the retryable errors is what puts the file back: the record of the file is removed and the next poll sees it again.</li><li>Found in the capture: a dead-lettered file's content is not in <code>processed-files.dat</code>. The idempotent consumer removes the key when the exception passes through it, even though <code>onException</code> handles it later. The download record is what keeps the file from coming back; a re-upload of the same broken file is dead-lettered again, which is what a person fixing it wants.</li></ul>")),
    (J + "IntegrationApplication.java", dwn("The two records and the queue.", "<code>FileIdempotentRepository</code> twice: downloaded files (name, size, time) and processed content (SHA-256).", "A restart that forgets.",
        "<ul><li>Shortcut: files on one server's disk. Two servers polling the same folder need a shared store, such as Camel's JDBC repository.</li></ul>")),
    (J + "PolicyFile.java", dwn("Reading a file.", "File-level problems throw <code>BadFileException</code>; line-level problems become rejected lines with reasons.", "One bad line losing a whole night's file, or a broken file half-sent.")),
    (J + "PolicyQueue.java", dwn("Sending.", "All of a file's lines, persistent, with <code>BANK:REFERENCE</code> as message id, then waits for the broker's confirms.", "A run marked done while the broker dropped the messages.",
        "<ul><li>If the broker fails part-way, the lines already sent are sent again on the retry, with the same ids: the reader drops the copies. Exactly once is not on offer; at least once with stable ids is.</li></ul>")),
    (J + "Runs.java", dwn("The runs.", "One JSON file per run in <code>data/runs/</code>, written to a temporary file and renamed.", "\"What happened to our file?\" with no answer.")),
    (J + "RunController.java", "<p><code>GET /integration/runs/{id}</code>.</p>"),
    (J + "PolicyRequest.java", "<p>One valid line, as the issuance team receives it.</p>"),
    ("src/main/resources/application.yaml", dwn("Settings.", "The bank's SFTP address, poll interval, retries, the data folder, publisher confirms.", "",
        "<ul><li>Demo rules: a password and <code>strictHostKeyChecking=no</code>. Production uses a private key and pins the bank's host key with <code>knownHostsFile</code>.</li></ul>")),
    ("compose.yaml", "<p>RabbitMQ 4.1 and the simulated bank's SFTP server, each with a health check.</p>"),
]
tree = """stations/104-enterprise-integration-with-apache-camel/
├── pom.xml, mvnw, mvnw.cmd, .mvn/, compose.yaml
├── src/main/java/com/bimaly/integration/
│   ├── PolicyFileRoute.java   ├── PolicyFile.java   ├── PolicyQueue.java   ├── PolicyRequest.java
│   ├── Runs.java   ├── RunController.java   └── IntegrationApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/bimaly/integration/   (see Tests)
├── data/                     made by the app: runs/, the two records, dead-letter/
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
""" + code("""docker compose up -d --wait  # RabbitMQ (5672, UI on 15672) and the bank's SFTP server (2222)
./mvnw spring-boot:run       # the route and http://localhost:8080
./mvnw test                  # all """ + str(N_TESTS) + """ tests; starts its own RabbitMQ and SFTP server""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""docker compose up -d --wait
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Drop a file in the bank's folder as the bank would, wait for the next poll, and read run 1:</p>
""" + code("""printf 'reference,customer_name,date_of_birth,product_code,sum_insured_paise\\nKB-1,Meera Iyer,1988-04-12,TERM10,1000000000\\n' \\
  | docker compose exec -T sftp sh -c 'cat > /home/koshbank/upload/KOSHBANK-20261024.part && mv /home/koshbank/upload/KOSHBANK-20261024.part /home/koshbank/upload/KOSHBANK-20261024.csv'
curl localhost:8080/integration/runs/1""", "bash") + """
<p>Stop the app, start it again, and wait for a poll: no run 2. Then delete <code>data/</code> while it is stopped and start once more: the file is processed again. That is what the record is for.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>Auth fail</code> in the log", "Wrong SFTP user or password.", "Compose's user is <code>koshbank</code> / <code>demo-only</code>."],
    ["<code>reject HostKey</code>", "The server's key is not in known_hosts.", "Demo: <code>strictHostKeyChecking=no</code>. Production: add the bank's key to a known_hosts file."],
    ["A file is never picked up", "Its name does not end in <code>.csv</code>, or it was seen before with the same name, size and time.", "Check <code>data/seen-files.dat</code>."],
    ["A run stays FAILED and repeats every poll", "The broker keeps refusing.", "Check RabbitMQ's alarms (disk, memory) and queue policies."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">The route first, then in the order a file travels.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>IntegrationRunContractTest</code> ({cnt('IntegrationRunContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>FileRestartTrapTest</code> ({cnt('FileRestartTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Messaging", "Duplicate delivery, retry and dead letter", f"<code>RetryAndDeadLetterMessagingTest</code> ({cnt('RetryAndDeadLetterMessagingTest')}), <code>DuplicateFileReplayTest</code>", '<span class="pill ok">pass</span>'],
    ["Idempotency", "The same request twice gives one effect", f"<code>DuplicateFileReplayTest</code> ({cnt('DuplicateFileReplayTest')}), and the restart in <code>FileRestartTrapTest</code>", '<span class="pill ok">pass</span>']]) + """
<p class="muted">Real servers: RabbitMQ 4.1 and an SFTP server (atmoz/sftp) in Docker. A restart is a real one: the app is started, stopped and started again. The broker's refusal is real too: a queue policy makes it reject every message. Polls every 200 ms and retries 100 ms apart keep the suite fast.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, Camel 4.23.0. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "FileRestartTrapTest.java", "<p>Written first: the old route and the app, each restarted.</p>"),
    (T + "IntegrationRunContractTest.java", "<p>Good and bad lines; the endpoint.</p>"),
    (T + "RetryAndDeadLetterMessagingTest.java", "<p>A refusing broker; files that can never be read.</p>"),
    (T + "DuplicateFileReplayTest.java", "<p>The same file again; a corrected file.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: fast polls, an empty queue, helpers.</p>"),
    (T + "Partners.java", "<p>RabbitMQ and the bank's SFTP server in Docker; uploads the way banks do them.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/bimaly/integration/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=RunsOfAFileChallengeTest</code> (Docker must be running).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "What happened to our file?", "Beginner-friendly", 20,
    "The bank's support line knows only the file's name. Add <code>GET /integration/runs?file=NAME</code>: every run of that file, oldest first; an empty list for a file never seen; <code>400</code> without <code>file</code>.",
    "both tests in <code>RunsOfAFileChallengeTest</code> pass.",
    ["<code>Runs.forFile</code> already exists.",
     "A required <code>@RequestParam</code> gives the <code>400</code> for free."],
    "challenge/RunsOfAFileChallengeTest.java", ["challenge/solution/RunController.java"]) + challenge(2, "Hold a suspicious file", "Go deeper", 35,
    "If more than 20% of the lines of a file of 10 lines or more are rejected, the bank's export is probably broken: send nothing, set the run to <code>HELD</code> with the reason \"3 of 10 lines were rejected; the limit is 20%.\", and copy the file as it arrived to <code>data/held/</code> for a person. Exactly 20% still goes through; smaller files are judged line by line.",
    "both tests in <code>HeldFileChallengeTest</code> pass.",
    ["A Camel <code>filter</code> after validation, ending in <code>stop()</code>.",
     "The body is the parsed file by then: keep the original bytes in an exchange property.",
     "Compare with whole numbers (<code>rejected × 100 &gt; lines × 20</code>), not doubles."],
    "challenge/HeldFileChallengeTest.java", ["challenge/solution/PolicyFileRoute.java", "challenge/solution/Runs.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Two servers, one folder</h2>
<p>For availability, the app now runs on two servers, and both poll the same bank folder. Each keeps its records on its own disk. Write down what happens when a file arrives, then design the fix: a shared store for the records (which, and what does \"add if absent\" need from it?), or only one server polling at a time (how is the other told to take over?). What does the issuance team see in each failure case?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the route with <code>noop=true</code>, restarted.</li>
<li>Record processed content on disk with an idempotent consumer; record downloaded files too.</li>
<li>Validate: file-level errors as one exception type, line-level errors as rejected lines.</li>
<li>Two <code>onException</code> blocks: dead letter for the first, retry-then-fail for everything else.</li>
<li>Send with confirms and stable ids; record each run.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Idempotent consumer, records on disk", "Two small files; one server only.", '<span class="pill ok">Chosen</span>'],
    ["<code>noop=true</code> alone", "Remembers in memory: forgotten at the next restart.", '<span class="pill bad">The trap</span>'],
    ["Move or delete files after reading", "Needs write access; a crash between send and move still repeats.", '<span class="pill warn">Where allowed, with a record</span>'],
    ["Records in a database (JDBC repository)", "A database to run; works for several servers.", '<span class="pill warn">Next step at scale</span>'],
    ["One dead-letter channel for every error", "A broker blip parks good files for a person.", '<span class="pill bad">Separate them</span>'],
    ["Keep the hand-written glue code", "4,000 lines to maintain; each pattern written again.", '<span class="pill bad">Replace</span>']]) + """
<h2>Database design</h2>
<p>No database in this station. What a table would hold is kept in files under <code>data/</code>:</p>
""" + table(["File", "Holds", "Why"], [
    ["<code>processed-files.dat</code>", "SHA-256 of each processed file's content", "The record that stops a second processing."],
    ["<code>seen-files.dat</code>", "name-size-time of each downloaded file", "Saves downloading every file after a restart."],
    ["<code>runs/N.json</code>", "One run per file picked up", "What happened, for people."],
    ["<code>dead-letter/</code>", "Files that can never be processed, as they arrived", "For a person to fix and ask the bank to resend."]]) + """
<p><strong>Boundaries:</strong> the content's key is added before the lines are sent and removed if sending fails, so a failed file is tried again. A file is <code>DONE</code> only after the broker confirmed every message.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["14. Operations: metric, alert, rollback, runbook, failure drill", "15. Real-world considerations"],
               "What changes when this runs for real.") + """
<h2>Real-world considerations</h2>
<dl class="facts">
<dt>Watching it</dt><dd>A file expected every night and not seen by 3 am is the alert that matters most: a missing file is silent. Count runs by status; any <code>DEAD_LETTERED</code> or repeated <code>FAILED</code> wants a person.</dd>
<dt>Half-written files</dt><dd>Banks upload as <code>.part</code> and rename. If a bank cannot, use Camel's read locks (<code>readLock=changed</code>) so a file still growing is not read.</dd>
<dt>Keys and secrets</dt><dd>An SSH key per bank, held in a secret store; the bank's host key pinned. Never <code>strictHostKeyChecking=no</code> outside a demo.</dd>
<dt>Growth of the records</dt><dd><code>FileIdempotentRepository</code> keeps up to 32 MB by default and then drops the oldest entries. A file older than that, uploaded again, would be processed again: size it, or move the records to a database.</dd>
<dt>More banks</dt><dd>One route per bank from the same builder, each with its own folder, user and records.</dd>
<dt>Exactly once</dt><dd>Not on offer between a file and a queue. At least once, with <code>BANK:REFERENCE</code> as message id, lets the reader drop copies.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is Apache Camel for?", "Integration routes: ready components (SFTP, file, AMQP, HTTP and hundreds more) and enterprise integration patterns, so the glue is a few lines instead of thousands."),
    ("What does noop=true do on a file or SFTP consumer?", "Leaves files where they are and turns on an idempotent repository so each is read once: by default in memory, so a restart reads them again."),
    ("What is an idempotent consumer?", "It records a key for each message handled and skips messages whose key it has seen. The key and the store decide what \"the same\" and \"remembered\" mean."),
    ("Which errors go to a dead-letter channel?", "The ones that will never succeed as they are: a broken file. Ones that may pass, like a broker outage, get retries and then come back later."),
    ("How do you know the broker has the messages?", "Publisher confirms: wait until the broker acknowledges each message before marking the work done."),
    ("How do you test a restart?", "Really restart: start the app, process, stop it, start a new one on the same data, and check nothing happens twice."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Idempotency", "A persistent record.", "You can say what counts as \"the same file\" and what the record's limits are."],
    ["Errors", "Retries and a dead-letter folder.", "Retryable and never-retry errors separated, each with a run status a person understands."],
    ["Camel", "A working route.", "You can read the route aloud as the business process it is."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("noop=true remembers in memory",
     "\"Camel's file components are idempotent with noop, so each file is only ever read once\": once per start. Its default record lives in memory. The next deployment reads the whole folder again, and every policy in it is sent a second time. A re-upload by the bank is not caught either.",
     "<code>theApiRemembersWhatItProcessedAcrossARestart</code>, <code>theSameFileUploadedAgainSendsNothingAndIsRecordedAsADuplicate</code> and <code>aCorrectedFileWithTheSameNameIsProcessed</code> fail."),
    ("A broker blip parks good files",
     "\"One error handler for everything: nothing is lost\": nothing is lost, but a file that failed only because the broker was busy for a minute is moved to the dead-letter folder and waits for a person, and its policies wait with it. Errors that pass should come back on their own.",
     "<code>aBrokerThatRefusesIsRetriedThenTheFileIsTriedAgainOnTheNextPoll</code> fails: the run is <code>DEAD_LETTERED</code>, never <code>DONE</code>."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate \"simplifies\" the route: \"noop already makes it idempotent, and one dead-letter channel means nothing is ever lost\". Read the file and list every problem before opening the findings.</p>
<p class="path">review/PolicyFileRoute.java</p>
""" + code(read("review/PolicyFileRoute.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed file copied over the real one, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">Until the first restart, the flawed version behaves. The first deployment after go-live is when the issuance team sees every policy twice.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
