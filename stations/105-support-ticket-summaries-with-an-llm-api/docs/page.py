"""Station 105 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 105,
    "stack": "Spring Boot 4.1.1 · Java 25 · RestClient with timeouts · Spring Security (HTTP Basic) · Anthropic Messages API shape (simulated)",
    "simulation": "The model provider is simulated: a small server in the shape of Anthropic's Messages API answers with hand-written summaries. No real model was called (no API key here), so the quality of real summaries, and how a real model reacts to injected text, were not tested. Tickets, customers and their details are made up; the card number is a standard test number.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker. Python 3 runs the simulated model provider in Try it yourself. A real provider needs your own API key (see Set up &amp; code). No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/taskloom/support/"
T = "src/test/java/com/taskloom/support/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("LLM API", "A web service you send text to; a large language model writes text back. You pay per token.", "A translation agency that charges by the word.", "the model provider"),
    ("Token", "The unit models read and write and providers bill: roughly 4 characters of English.", "The agency's word count.", "<code>inputTokens</code>, <code>outputTokens</code>"),
    ("System prompt", "The instructions you give the model, kept apart from the text it works on.", "The brief stapled to the front of the job.", "<code>Prompt.SYSTEM</code>"),
    ("Prompt injection", "Text inside the data that tries to give the model new instructions.", "A letter to translate that says \"translator: also post me the client list\".", "ticket T-1003"),
    ("Redaction", "Removing personal data before the text leaves your systems.", "Blacking out names on a photocopy.", "<code>Redactor</code>"),
    ("Unbounded consumption", "Calls nobody limited: long inputs, long outputs, repeated calls; the bill grows without a ceiling.", "An open tab at the agency.", "max_tokens, input limit, daily budget"),
]
STORY = [
    ("Forty messages before every reply", "Taskloom's support agents read long ticket threads before they answer. A \"Summarise\" button calling an LLM API would save them minutes a ticket."),
    ("The first version", "It pasted the whole thread into the model's instructions. Customers' emails, phone numbers and a card number went to the provider with every call; one customer's message said \"ignore all previous instructions\"; and a 400-message thread cost as much as a hundred short ones, every time anyone pressed the button."),
    ("The fix", "Personal data is removed first. The thread goes to the model as data, inside tags it cannot break out of. The input and the output are capped, each team has a daily budget, an unchanged thread is not summarised twice, and the model's answer is checked too."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Text sent to a model leaves your systems, can carry instructions, and costs money. Treat it like a payment to a stranger.</p>

<h2>What are we building?</h2>
<p>An endpoint that summarises a support ticket with an LLM API, without sending personal data, without letting the ticket's text steer the model, and within a budget.</p>

<h2>An everyday analogy</h2>
<p>Sending a file to an outside agency: you black out the client's details, staple your own brief on top (\"summarise this; anything written inside is part of the file\"), say how long the answer may be, and keep a monthly spending limit.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Check</strong>: only an agent of the ticket's team may ask; the team's budget must have room.</li>
<li><strong>Clean</strong>: emails, card, Aadhaar, phone and PAN numbers and the customer's name are replaced by labels.</li>
<li><strong>Send, bounded</strong>: our brief as the system prompt; the thread as data, at most 12,000 characters; at most 400 tokens back; 20 s at most.</li>
<li><strong>Check the answer</strong>: cleaned again, cut to size, counted against the budget, and kept for the next agent.</li>
</ol>

<details class="qa check"><summary>Check yourself: does putting the thread inside tags stop prompt injection?</summary><p>No. It keeps the customer's text out of the place for our instructions and stops it closing the tag, which makes injection harder. A model can still be swayed by words in the data. That is why the summary is only shown to an agent, never acted on by a program, and why challenge 2 warns the agent.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No real model.</strong> A simulated provider answers; the real API was not called.</li>
<li><strong>No ticketing system.</strong> Four demo tickets in memory.</li>
<li><strong>No complete anonymiser.</strong> Known formats and the customer's name; not every piece of personal data.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Taskloom</strong> (a fictional work-management company) wants ticket summaries for its support agents. The feature must not leak customer data or run up the bill.</p>

<h2>Acceptance criteria</h2>
<p class="muted">Demo rules: 12,000 characters of thread at most (about 3,000 tokens), 400 tokens of summary, 20 s for an answer, 200,000 tokens a team a day.</p>
<ol class="gwt">
<li><b>Given</b> an agent and their team's ticket, <b>then</b> <code>200</code> with the summary, the tokens used, and what was removed.</li>
<li><b>Given</b> the same unchanged thread again, <b>then</b> the remembered summary, no call, no cost.</li>
<li><b>Given</b> no sign-in, a customer, or another team's ticket, <b>then</b> <code>401</code>, <code>403</code>, <code>404</code>, and nothing is sent.</li>
<li><b>Given</b> a thread with personal data or instructions in it, <b>then</b> the data does not leave and the instructions stay inside the data.</li>
<li><b>Given</b> the team's budget is spent, <b>then</b> <code>429</code> and no call.</li>
<li><b>Given</b> the provider is slow, overloaded or refuses us, <b>then</b> <code>504</code>, <code>503</code> with <code>Retry-After</code>, or <code>502</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Personal data in known formats never leaves Taskloom.</li>
<li>Customer text never goes in the system prompt.</li>
<li>Every call has an input limit, an output limit, a timeout and a budget.</li>
<li>Prompts and summaries are not written to logs.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Call an LLM API with RestClient, with timeouts and its error codes.</li>
<li>Remove personal data before sending, and know what redaction misses.</li>
<li>Keep instructions and data apart; treat the model's answer as untrusted.</li>
<li>Bound cost: input, output, budget, caching.</li>
<li>Map the work to three OWASP LLM risks: prompt injection, sensitive information disclosure, unbounded consumption.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/tickets/{id}/summary</code>", "Summarise a ticket. HTTP Basic; agents only, their own team's tickets."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "A summary (<code>cached: true</code> when the thread has not changed)"],
    ['<span class="pill warn">400</span>', "The id is not <code>T-</code> and four digits"],
    ['<span class="pill warn">401</span> / <span class="pill warn">403</span>', "No or wrong sign-in / not an agent"],
    ['<span class="pill warn">404</span>', "No such ticket, or another team's: the same answer, so ids cannot be probed"],
    ['<span class="pill warn">429</span>', "The team's daily budget is spent"],
    ['<span class="pill warn">502</span> / <span class="pill warn">503</span> / <span class="pill warn">504</span>', "The provider refused our request / is busy (<code>Retry-After: 60</code>) / did not answer in 20 s"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """, in this order, against <code>docs/test-model.py</code>, a simulated provider that answers a hand-written summary per ticket and counts tokens roughly (4 characters a token). <code>Date</code>, connection and standard security headers are left out.</p>
""" + examples([
    ("01-a-billing-agent-asks-for-a-summary", "Case 1: a billing agent asks for T-1001", "<b>Why:</b> <code>200</code>; <code>removed</code> counts what never left."),
    ("02-another-agent-asks-again", "Case 2: a colleague asks for the same ticket", "<b>Why:</b> unchanged thread: remembered, 0 tokens."),
    ("03-a-ticket-with-instructions-in-it", "Case 3: T-1003, where a message tries to give the model orders", "<b>Why:</b> the simulated provider answers a fixed summary, so this says nothing about how a model treats the text. What matters is what was sent: see below."),
    ("04-a-400-message-thread", "Case 4: a 400-message thread", "<b>Why:</b> the first message and the newest that fit; <code>omittedMessages</code> says how many were left out."),
    ("05-another-teams-ticket", "Case 5: a shipping agent asks for a billing ticket", "<b>Why:</b> <code>404</code>, as if it did not exist."),
    ("06-a-customer-asks", "Case 6: a customer signs in and asks", "<b>Why:</b> <code>403</code>."),
    ("07-no-sign-in", "Case 7: no sign-in", "<b>Why:</b> <code>401</code>."),
    ("08-no-such-ticket", "Case 8: no such ticket", "<b>Why:</b> <code>404</code>."),
    ("09-not-a-ticket-id", "Case 9: not a ticket id", "<b>Why:</b> <code>400</code>; nothing sent."),
    ("10-the-provider-is-overloaded", "Case 10: the provider answers 529 (overloaded)", "<b>Why:</b> <code>503</code> with <code>Retry-After</code>; not retried, every call costs."),
    ("11-the-provider-hangs", "Case 11: the provider hangs for 30 s", "<b>Why:</b> <code>504</code> after 20 s."),
]) + code(read("docs/captures/hang-timing.txt").strip(), "text") + """
<h2>What left Taskloom</h2>
<p class="muted">The requests exactly as the simulated provider received them (the API key's length only). T-1001: personal data replaced by labels. T-1003: the customer's <code>&lt;/ticket&gt;</code> arrives escaped, inside our tags, and our system prompt is unchanged.</p>
""" + code(read("docs/captures/sent-T-1001.txt").strip(), "text") + code(read("docs/captures/sent-T-1003.txt").strip(), "text") + code(read("docs/captures/sent-T-1004.txt").strip(), "text")

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["The old request", "Email, phone, card, PAN, name, injected text and 50,000+ characters sent", "<code>theOldWaySendsPersonalDataAndTheWholeThreadAsInstructions</code>"],
    ["The API's request", "None of it; our system prompt; 12,000 characters; 400 tokens", "<code>theApiSendsNoneOfItAndBoundsTheCost</code>"],
    ["A summary, then the same again", "<code>200</code> with counts; then cached, one call in all", "<code>anAgentGetsASummaryOfTheirTeamsTicketAndAnUnchangedThreadCostsNothing</code>"],
    ["A changed thread", "Summarised again", "<code>aChangedThreadIsSummarisedAgain</code>"],
    ["Unknown ticket; bad id", "<code>404</code>; <code>400</code>; nothing sent", "<code>anUnknownTicketIs404AndABadIdIs400</code>"],
    ["Slow, overloaded, refusing provider", "<code>504</code> in about 1 s (the test limit); <code>503</code>; <code>502</code>", "<code>aSlowModelIs504ABusyOne503AndARefusalIs502</code>"],
    ["No sign-in; wrong password", "<code>401</code>", "<code>noSignInOrAWrongPasswordIs401</code>"],
    ["A customer", "<code>403</code>", "<code>aCustomerIs403</code>"],
    ["Another team's ticket", "<code>404</code>; nothing sent", "<code>anotherTeamsTicketIsNotFoundAndNothingIsSent</code>"],
    ["Injected text; personal data in the answer", "Escaped inside the tags; the answer cleaned", "<code>textInTheTicketStaysDataAndTheModelsAnswerIsCleanedToo</code>"],
    ["The team's budget spent", "<code>429</code>, no call; cached still served; other teams unaffected", "<code>whenTheTeamsBudgetIsSpentTheAnswerIs429AndTheModelIsNotCalled</code>"],
    ["Formats: email, phone, card, Aadhaar, PAN, name", "Replaced and counted", "<code>knownFormatsAndTheCustomersNameAreRemoved</code>"],
    ["Order numbers, times, dates, amounts", "Kept", "<code>numbersThatAreNotCardsOrPhonesAreKept</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Sending personal data and untrusted text to the model with no cost limit.</p>
<ul>
<li><strong>The old way.</strong> \"Summarise this support ticket:\" and the whole thread, as written, in the system prompt, with 4,096 output tokens allowed. The test reads what the provider received: the customer's email, phone, card and PAN numbers and name; their \"Ignore all previous instructions\" sitting where our instructions go; and more than 50,000 characters for the long thread, on every press of the button.</li>
<li><strong>The API.</strong> The same tickets: none of those strings arrive, the system prompt is ours alone, the long thread is cut to 12,000 characters around the first and newest messages, and 400 tokens is the most it can write.</li>
</ul>
<p>While building, each part was undone once: no redaction turned 2 tests red; no escaping 1; no input limit 1; no budget check 1; no remembered summaries 2; the answer not cleaned 1; no team check 1; no read timeout 1; provider errors not mapped 1; cards without the Luhn check 1; any signed-in user allowed 1.</p>
</div>
""" + code(read(T + "SummaryLeakTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "SummaryController.java", dwn("The endpoint.", "The team check, and one status with a plain sentence for each provider failure.", "Another team's tickets; 500s for a busy provider.")),
    (J + "Summaries.java", dwn("The flow.", "Prompt, remembered summary, budget, call, charge, clean the answer, log counts only.", "A bill nobody limited; summaries with personal data; prompts in the logs.")),
    (J + "Prompt.java", dwn("What is sent.", "Our instructions alone in <code>system</code>; the thread, cleaned and escaped, inside <code>&lt;ticket&gt;</code>; the first message plus the newest that fit.", "Customer text in the place for instructions; a message that closes the tag.")),
    (J + "Redactor.java", dwn("Removing personal data.", "Email, card (Luhn-checked), Aadhaar, Indian mobile, PAN, the customer's name.", "Contact and identity numbers at the provider.",
        "<ul><li>Patterns lower the risk; they do not remove it. A home address, another person's name or a number written in words gets through. For more, a dedicated PII-detection service, and the provider's data terms (challenge 3).</li></ul>")),
    (J + "ModelClient.java", dwn("The provider.", "Anthropic's Messages API shape: <code>x-api-key</code>, <code>anthropic-version</code>, <code>max_tokens</code>. Connect 2 s, answer 20 s. 429, 529 and 5xx are busy; other 4xx are our mistake.", "A request thread waiting for ever; a paid call retried in a loop.")),
    (J + "TeamBudget.java", dwn("The budget.", "Tokens per team per day (India time), checked before and charged after.", "Unbounded consumption.",
        "<ul><li>A limit, not an exact figure: requests already running when it is reached still finish. Shortcut: in memory, one server.</li></ul>")),
    (J + "SecurityConfig.java", "<p>HTTP Basic, demo users; agents carry their team in the sign-in, never in the request.</p>"),
    (J + "Tickets.java", "<p>Four demo tickets.</p>"),
    ("src/main/resources/application.yaml", dwn("Settings.", "The provider's address, key and model id from environment variables; limits and timeouts.", "A key in the source code.")),
]
tree = """stations/105-support-ticket-summaries-with-an-llm-api/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/taskloom/support/
│   ├── SummaryController.java   ├── Summaries.java   ├── Prompt.java   ├── Redactor.java
│   ├── ModelClient.java   ├── TeamBudget.java   ├── SecurityConfig.java   ├── ProblemResponses.java
│   └── Tickets.java, SupportApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/taskloom/support/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, simulated provider, captures, saved runs"""
codetab = belongs(["Set up and run: commands for Windows and macOS/Linux, troubleshooting", "Try it yourself",
                   "10. Complete working code, in the order a request travels", "11. Code explanation"],
                  "Level 2. Every command here was run and gave the results shown, against the simulated provider.") + """
<h2>Set up and run</h2>
""" + table(["You need", "Version", "Check with"], [
    ["JDK", "25 (recommended). JDK 21 also works, see below", "<code>java -version</code>"],
    ["Python 3", "Only for the simulated provider", "<code>python3 --version</code>"],
    ["Maven", "Not needed: the project ships the Maven wrapper", ""]]) + """
<p><strong>macOS / Linux</strong></p>
""" + code("""python3 docs/test-model.py 9077 &   # the simulated provider
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests; they start their own simulated provider""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code("""Start-Process python -ArgumentList 'docs/test-model.py','9077'
.\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<p><strong>A real provider</strong> (not tried here: no key). Set <code>TASKLOOM_MODEL_URL=https://api.anthropic.com/v1/messages</code>, <code>TASKLOOM_MODEL_API_KEY</code> to your key and <code>TASKLOOM_MODEL_NAME</code> to a model id from the provider's documentation. Every call then costs money: start with the demo budget.</p>
<h2>Try it yourself</h2>
""" + code("""curl -X POST -u priya:priya-demo-pass localhost:8080/tickets/T-1001/summary
python3 -m json.tool sent-T-1001.json   # test-model.py saves each request it received, in the folder it was started from""", "bash") + """
<p>Read the saved request: no email, no card number. Then copy the Review tab's <code>Prompt.java</code> over the real one, restart, and look again.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>502</code> and \"refused the request: 401\" in the log", "Wrong or missing API key.", "Set <code>TASKLOOM_MODEL_API_KEY</code>; never put it in the yaml."],
    ["<code>503</code> often", "The provider is overloaded or your account's rate limit is reached.", "Wait for <code>Retry-After</code>; ask the provider for a higher limit."],
    ["<code>429</code> from the API", "The team's budget is spent.", "Raise <code>taskloom.budget.tokens-per-team-per-day</code> deliberately, or wait until midnight (India time)."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the configuration.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>SummaryContractTest</code> ({cnt('SummaryContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>SummaryLeakTrapTest</code> ({cnt('SummaryLeakTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, another user's data, malicious input", f"<code>SummarySecurityTest</code> ({cnt('SummarySecurityTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "Unbounded consumption; redaction formats", f"<code>SummaryBudgetTest</code> ({cnt('SummaryBudgetTest')}), <code>RedactorTest</code> ({cnt('RedactorTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="muted">The simulated provider records every request exactly as it arrived, so the tests check what left Taskloom, not what the code meant to send. It does not imitate a model's reasoning: these tests cannot show how a real model treats injected text. That needs a real model, an API key, and evaluation runs (not done here).</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "SummaryLeakTrapTest.java", "<p>Written first: the old request and the API's, side by side.</p>"),
    (T + "SummaryContractTest.java", "<p>Summaries, caching, bad ids, provider failures.</p>"),
    (T + "SummarySecurityTest.java", "<p>Sign-in, roles, teams, injected text.</p>"),
    (T + "SummaryBudgetTest.java", "<p>The daily budget.</p>"),
    (T + "RedactorTest.java", "<p>What is removed and what is kept.</p>"),
    (T + "TestModel.java", "<p>The simulated provider.</p>"),
    (T + "ApiTest.java", "<p>Shared setup.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/taskloom/support/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=BudgetLeftChallengeTest</code>.</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "How much is left today?", "Beginner-friendly", 20,
    "Agents only learn about the budget from a <code>429</code>. Add <code>teamTokensLeftToday</code> to every summary: the team's limit minus what it used today, never below 0; a remembered summary spends nothing.",
    "both tests in <code>BudgetLeftChallengeTest</code> pass.",
    ["Add <code>left(team)</code> to <code>TeamBudget</code>: <code>Math.max(0, limit - used)</code>.",
     "Read it after charging, so the answer includes this call."],
    "challenge/BudgetLeftChallengeTest.java", ["challenge/solution/Summaries.java", "challenge/solution/TeamBudget.java"]) + challenge(2, "Warn the agent", "Go deeper", 30,
    "Escaping keeps a message inside the tags, but a model may still follow it. When a message contains phrases often used to steer a model (\"ignore previous instructions\", \"system prompt\", \"you are now\"), add a warning naming the message, so the agent reads the ticket before acting on the summary.",
    "both tests in <code>InjectionWarningChallengeTest</code> pass.",
    ["Check the original messages, not the cleaned prompt.",
     "Case-insensitive; one warning per message.",
     "Name it for what it is: a warning for a person, not a defence. New wordings will get past any list."],
    "challenge/InjectionWarningChallengeTest.java", ["challenge/solution/Summaries.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>What may leave Taskloom?</h2>
<p>Legal asks before launch: which data reaches the provider, where it is processed and stored, for how long, and whether it is used for training. Write the one-page answer: what the redactor removes and misses, which provider terms you need (retention, training, region), what India's DPDP Act asks of you as the data fiduciary, and what you would log to prove it later without logging the text itself.</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design: tables, constraints, transaction boundary"],
                 "The learner decides the design here, before opening the Code tab.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: send the old request to a recording provider and read what arrived.</li>
<li>Redact; move the thread out of the system prompt into escaped tags.</li>
<li>Bound it: input characters, output tokens, timeouts, a budget, caching.</li>
<li>Treat the answer as untrusted: clean it, cut it, show it to a person only.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["RestClient against the provider's HTTP API", "A small client to write; full control of every field.", '<span class="pill ok">Chosen</span>'],
    ["Spring AI", "Less code, many providers; another dependency and its own defaults to learn.", '<span class="pill warn">Fine too</span>'],
    ["Send the thread as written", "Personal data at a third party, on every call.", '<span class="pill bad">The trap</span>'],
    ["A self-hosted model", "Data stays home; GPUs and operations to pay for.", '<span class="pill warn">When data may not leave</span>'],
    ["Summarise on every view", "Cost grows with views, not with changes.", '<span class="pill bad">Cache by content</span>']]) + """
<h2>Database design</h2>
<p>No database in this station. The remembered summaries and the budget are in memory (one server); with several servers both belong in a shared store, the budget with an atomic increment.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["14. Operations: metric, alert, rollback, runbook, failure drill", "15. Real-world considerations"],
               "What changes when this runs for real.") + """
<h2>Real-world considerations</h2>
<dl class="facts">
<dt>OWASP Top 10 for LLM Applications (2025)</dt><dd>A community list from the OWASP GenAI Security Project, not a formal standard. This station covers LLM01 Prompt Injection (instructions kept apart, escaping, a person reads the result), LLM02 Sensitive Information Disclosure (redaction, no text in logs) and LLM10 Unbounded Consumption (input and output limits, timeouts, budget, cache), and touches LLM05 Improper Output Handling (the answer is cleaned and never executed).</dd>
<dt>The provider's terms</dt><dd>Retention, training use and processing region are contract questions, not code. Read them before the first real call (challenge 3).</dd>
<dt>Watching cost</dt><dd>Count tokens by team and by day from the <code>usage</code> the provider returns; alert at 80% of a budget, not at 100%.</dd>
<dt>Quality</dt><dd>Keep a set of real (redacted) tickets and check summaries against it when the prompt or the model changes. Not done here: there is no real model.</dd>
<dt>Retries</dt><dd>None automatic. A busy provider gets <code>Retry-After</code>; the agent decides. Automatic retries multiply cost exactly when the provider is struggling.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is prompt injection, and can you prevent it?", "Text in the data that tries to instruct the model. You can make it harder (instructions apart, data in escaped tags, no tools or actions on the output) but not rule it out; a person must judge the result."),
    ("What personal data should leave your system for an LLM call?", "As little as the task needs. Remove what you can recognise before sending, and know your provider's retention and training terms."),
    ("How do you stop an LLM feature running up the bill?", "Limit input and output, set timeouts, budget per team or user, cache unchanged inputs, and do not retry automatically."),
    ("Why not put the ticket in the system prompt?", "That is where the model looks for its instructions; customer text there competes with yours."),
    ("How do you test an LLM integration without a model?", "A recording fake provider: assert on exactly what was sent, and on how each answer and error is handled. Model behaviour needs separate evaluations with a real model."),
    ("What do you log?", "Who asked, which ticket, tokens, latency, outcome. Never the prompt or the answer."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You ran the flawed version and explained each failure."],
    ["Data", "Known formats removed.", "You can say what the redactor misses and what the contract must cover."],
    ["Injection", "Instructions and data apart.", "You explain why it is still not solved and what limits the damage."],
    ["Cost", "max_tokens set.", "Input, output, time, budget and cache, each with a number you can defend."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("Personal data sent as written",
     "\"The provider does not train on API data, so masking would only make the summaries worse\": training is one question; the data still leaves Taskloom, is stored for a while under the provider's terms, and crosses a border. Emails, phone, card and PAN numbers are not needed for a summary.",
     "<code>theApiSendsNoneOfItAndBoundsTheCost</code> and <code>anAgentGetsASummaryOfTheirTeamsTicketAndAnUnchangedThreadCostsNothing</code> fail."),
    ("A message can close the tag",
     "With the escaping gone, a customer who writes <code>&lt;/ticket&gt;</code> ends the data early: what follows reads as if Taskloom wrote it.",
     "<code>textInTheTicketStaysDataAndTheModelsAnswerIsCleanedToo</code> fails."),
    ("No budget",
     "\"max_tokens already caps what one summary can cost\": one, yes. Nothing caps how many: a script, a stuck button or a busy day multiplies the bill.",
     "<code>whenTheTeamsBudgetIsSpentTheAnswerIs429AndTheModelIsNotCalled</code> fails."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate \"simplifies\" the feature: \"the provider does not train on API data, and max_tokens caps the cost\". Read both files and list every problem before opening the findings.</p>
<p class="path">review/Prompt.java</p>
""" + code(read("review/Prompt.java"), "java") + """
<p class="path">review/Summaries.java</p>
""" + code(read("review/Summaries.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">The flawed version gives the same summaries, arguably better ones. Nothing in a demo shows the data that left or the bill that grew.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
