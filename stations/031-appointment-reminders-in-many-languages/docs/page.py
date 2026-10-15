"""Station 031 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 31,
    "stack": "Spring Boot 4.1.1 · Java 25 · MessageSource · message bundles · Accept-Language · Locale.lookup · Indian number formatting · MockMvc",
    "simulation": "Appointments, patients and amounts are demo data, not Mediqo's. The endpoint builds the reminder text only; no SMS or message is sent. The Hindi text was written for this demo and should be reviewed by a native speaker before real use.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/mediqo/reminders/"
T = "src/test/java/com/mediqo/reminders/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Message bundle", "A file of texts for one language, each under a key.", "The same notice printed in two languages on a hospital wall.", "<code>messages_hi.properties</code>"),
    ("Placeholder", "A numbered gap in a message that the app fills: <code>{0}</code>, <code>{1}</code>.", "Blanks in a form letter.", "<code>{0}</code> is the patient's name"),
    ("Locale", "A language plus regional conventions: month names, digits, separators.", "Writing a date the way people in that place read it.", "<code>hi-IN</code>"),
    ("Accept-Language", "A header the phone or browser sends to say which languages the user reads.", "Telling the receptionist \"Hindi please, English is fine too\".", "<code>hi-IN,hi;q=0.9,en;q=0.8</code>"),
    ("Fallback language", "The language used when we have no text in the one asked for.", "Using the English leaflet when the Tamil one has run out.", "English, <code>messages.properties</code>"),
    ("Lakh grouping", "Indian digit grouping: the last three digits, then pairs.", "₹1,23,456 is one lakh twenty-three thousand.", "<code>IndianRupees</code>"),
]
STORY = [
    ("A reminder goes out", "Asha prefers Hindi. The app sends her: \"नमस्ते Asha, आपका अपॉइंटमेंट डॉ. Mehta के साथ 20 October 2026। कृपया भुगतान करें 123456.5\"."),
    ("Three things are wrong", "The sentence was glued from Hindi pieces in English word order, the month is in English, and 123456.5 has no rupee sign, no grouping and one decimal. Asha calls the clinic to ask what she owes."),
    ("The fix", "One whole sentence per language with numbered blanks, the date formatted in the patient's language, and the amount written the Indian way: ₹1,23,456.50."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Translate whole sentences, and format numbers and dates for the reader, not for the server.</p>

<h2>What are we building?</h2>
<p><code>GET /appointments/{id}/reminder</code> returns the reminder text for an appointment in the right language: the one asked for with <code>?lang</code>, else the phone's language, else the patient's own preference. If we do not have that language, English.</p>

<h2>An everyday analogy</h2>
<p>A wedding card printed in two languages. The Hindi side is not the English side with words swapped one by one; someone wrote the whole Hindi text, and only the names and the date are filled in.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Pick the language</strong>: <code>?lang</code>, then the <code>Accept-Language</code> header, then the patient's preference.</li>
<li><strong>Match it</strong> to the languages we have (English, Hindi); anything else becomes English.</li>
<li><strong>Format the pieces</strong>: the date in that language, the amount as Indian rupees.</li>
<li><strong>Fill the sentence</strong> for that language, where the translator decided the word order.</li>
</ol>

<details class="qa check"><summary>Check yourself: why not translate "Hello", "your appointment with" and "is on" separately and join them?</summary><p>Languages order words differently. Hindi puts the verb at the end and uses endings like "के साथ" after the name. Joined fragments follow English order, so the sentence is wrong in every language but English.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No sending.</strong> The text is built; no SMS or WhatsApp message is sent.</li>
<li><strong>No translation service.</strong> The texts are written by people and kept in files.</li>
<li><strong>Two languages.</strong> English and Hindi; challenge 1 adds Marathi.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Mediqo</strong> (a fictional clinic chain) sends appointment reminders. Hindi-speaking patients get sentences glued from fragments, with English month names, and amounts like 123456.5 instead of ₹1,23,456.50.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> <code>?lang=en</code> and a Hindi <code>Accept-Language</code>, <b>then</b> the reminder is in English: <code>lang</code> wins.</li>
<li><b>Given</b> no <code>lang</code> and <code>Accept-Language: hi-IN,hi;q=0.9,en;q=0.8</code>, <b>then</b> Hindi.</li>
<li><b>Given</b> neither, <b>then</b> the patient's preferred language: Hindi for Asha, English for Ravi.</li>
<li><b>Given</b> Tamil, which we do not have, <b>then</b> English, and the response still says Tamil was requested.</li>
<li><b>Given</b> Asha's ₹1,23,456.50 appointment on 20 October 2026 at 10:30, in Hindi, <b>then</b> exactly: <span lang="hi">नमस्ते Asha, डॉ. Mehta के साथ आपका अपॉइंटमेंट 20 अक्टूबर 2026 को 10:30 बजे है। कृपया क्लिनिक में ₹1,23,456.50 का भुगतान करें।</span></li>
<li><b>Given</b> an unknown appointment, <b>then</b> <code>404</code>; a <code>lang</code> that is not a language tag, <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>One complete sentence per language, with numbered placeholders; every key in every bundle, with the same placeholders.</li>
<li>English is the only fallback, whatever language the server itself runs in.</li>
<li>Money stays in integer paise until it is formatted: ₹, lakh and crore grouping, two decimals.</li>
<li>Times are 24-hour (<code>10:30</code>, <code>15:00</code>), so no translated AM/PM is needed.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Use Spring's <code>MessageSource</code> with message bundles and placeholders.</li>
<li>Choose a language from <code>Accept-Language</code> with <code>Locale.lookup</code>.</li>
<li>Format dates with a <code>Locale</code>, and know where Java's number formatting stops (lakh grouping).</li>
<li>Control the fallback language.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/appointments/{id}/reminder?lang=hi</code>", "The reminder text. <code>lang</code> is optional; so is the <code>Accept-Language</code> header."]]) + """
<h2>Response fields</h2>
""" + table(["Field", "Meaning"], [
    ["<code>language</code>", "The language the text is in: <code>en</code> or <code>hi</code>."],
    ["<code>requestedLanguage</code>", "What was asked for (or the patient's preference). Differs from <code>language</code> after a fallback, so a dashboard can count missing translations."],
    ["<code>text</code>", "The reminder."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "A reminder, in the chosen language or in English after a fallback"],
    ['<span class="pill warn">400</span>', "<code>lang</code> is not a language tag such as <code>hi</code> or <code>hi-IN</code>"],
    ['<span class="pill warn">404</span>', "No such appointment"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-the-patients-own-language", "Case 1: Asha, nothing asked for", "<b>Why:</b> no <code>lang</code>, no header: her preference, Hindi. Month in Hindi, amount in lakhs."),
    ("02-lang-asks-for-english", "Case 2: Asha, <code>?lang=en</code>", "<b>Why:</b> <code>lang</code> wins over her preference. The amount is still grouped the Indian way."),
    ("03-the-phone-asks-for-hindi", "Case 3: Ravi's phone is set to Hindi", "<b>Why:</b> the header beats his saved preference (English)."),
    ("04-a-language-we-do-not-have", "Case 4: <code>?lang=ta</code>", "<b>Why:</b> no Tamil bundle yet: English, and <code>requestedLanguage</code> says Tamil was asked for."),
    ("05-no-such-appointment", "Case 5: appointment 999", "<b>Why:</b> <code>404</code>."),
    ("06-a-lang-that-is-not-a-language", "Case 6: <code>?lang=hindi-language</code>", "<b>Why:</b> not a language tag: <code>400</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["<code>lang</code> and a header disagree", "<code>lang</code> wins", "<code>theLangParameterWins</code>"],
    ["Only a header, with weights", "The best language we have", "<code>withoutLangTheAcceptLanguageHeaderDecides</code>"],
    ["Nothing asked", "The patient's preference", "<code>withNeitherThePatientsPreferenceDecides</code>"],
    ["Tamil; a header of Tamil and Malayalam", "English, with the request recorded", "<code>aLanguageWeDoNotHaveFallsBackToEnglish</code>"],
    ["A server whose own locale is Hindi", "The fallback is still English", "<code>theServersOwnLocaleNeverDecidesTheFallback</code>"],
    ["A malformed <code>Accept-Language</code>", "English, not an error", "<code>languageMatchingFollowsAcceptLanguageRules</code>"],
    ["₹0.05, ₹999.99, ₹1,000.00 up to ₹10,00,00,000.00", "Indian grouping, two decimals", "<code>rupeesAreGroupedInLakhsAndCrores</code>"],
    ["A message missing from the Hindi bundle, or a placeholder dropped", "A test fails before release", "<code>everyEnglishMessageHasAHindiOneWithTheSamePlaceholders</code>"],
    ["Appointment 999; <code>lang=&lt;script&gt;</code>", "<code>404</code>; <code>400</code>", "<code>anUnknownAppointmentIs404AndAMalformedLangIs400</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Concatenating translated fragments, and formatting numbers without the locale.</p>
<p>The first test rebuilds the old reminder: the Hindi text ends in <code>123456.5</code>, contains "October", and has lost the verb ending. The second shows the obvious fix is not enough: Java's own <code>en-IN</code> currency format gives <code>₹123,456.50</code>, grouped in threes, because <code>DecimalFormat</code> has a single grouping size. The third checks the real Hindi sentence word for word. While building, each fix was undone once: Java's formatter instead of <code>IndianRupees</code> turned 4 tests red, English dates everywhere 5, ignoring the header 2, and falling back to the server's locale 1.</p>
</div>
""" + code(read(T + "ConcatenatedReminderTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "ReminderController.java", dwn("Chooses the language, formats the date and amount, and fills the sentence.",
        "<code>Locale.lookup</code> applies <code>Accept-Language</code> weights for us; anything unmatched or malformed is English.",
        "Joining fragments: the word order is then English in every language.",
        "<ul><li>The formatting locale is <code>&lt;language&gt;-IN</code>: Hindi month names with India's conventions.</li><li><code>@Pattern</code> on <code>lang</code> refuses anything that is not a language tag.</li></ul>")),
    (J + "IndianRupees.java", dwn("Paise to <code>₹1,23,456.50</code>.",
        "Integer arithmetic only; the grouping is done by hand because Java's formatter cannot do it.",
        "<code>paise / 100.0</code> printed as a double, or <code>NumberFormat</code> for <code>en-IN</code>.")),
    ("src/main/resources/messages.properties", "<p>English, the fallback: one sentence, five placeholders.</p>"),
    ("src/main/resources/messages_hi.properties", "<p>Hindi: the same placeholders in Hindi word order. Saved as UTF-8.</p>"),
    ("src/main/resources/application.yaml", "<p>The bundle name, UTF-8, and no fallback to the server's own locale.</p>"),
    (J + "Appointments.java", "<p>Two demo appointments, each with the patient's preferred language.</p>"),
    (J + "RemindersApplication.java", "<p>Entry point.</p>"),
]
tree = """stations/031-appointment-reminders-in-many-languages/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/mediqo/reminders/
│   ├── ReminderController.java   ├── IndianRupees.java
│   ├── Appointments.java         └── RemindersApplication.java
├── src/main/resources/
│   ├── application.yaml   ├── messages.properties   └── messages_hi.properties
├── src/test/java/com/mediqo/reminders/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs"""
codetab = belongs(["Set up and run: commands for Windows and macOS/Linux, troubleshooting", "Try it yourself",
                   "10. Complete working code, in the order a request travels", "11. Code explanation"],
                  "Level 2. Every command here was run and gave the results shown.") + """
<h2>Set up and run</h2>
""" + table(["You need", "Version", "Check with"], [
    ["JDK", "25 (recommended). JDK 21 also works, see below", "<code>java -version</code>"],
    ["Maven", "Not needed: the project ships the Maven wrapper", ""],
    ["Docker", "Not needed for this station", ""]]) + """
<p><strong>macOS / Linux</strong></p>
""" + code("""./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all """ + str(N_TESTS) + """ tests""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code(""".\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Ask as a phone set to Hindi would, then as one set to Tamil:</p>
""" + code("""curl http://localhost:8080/appointments/502/reminder -H "Accept-Language: hi-IN,hi;q=0.9,en;q=0.8"
curl http://localhost:8080/appointments/502/reminder -H "Accept-Language: ta-IN" """, "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Hindi shows as <code>à¤¨à¤®...</code> or <code>?????</code>", "The bundle was read as ISO-8859-1, or the terminal is not UTF-8.", "Keep <code>spring.messages.encoding: UTF-8</code> and save bundles as UTF-8. On Windows, run <code>chcp 65001</code> before curl."],
    ["The key itself (<code>reminder.text</code>) appears, or <code>NoSuchMessageException</code>", "The key is missing from <code>messages.properties</code>.", "Add it to the English file first: it is the fallback for every language."],
    ["A message shows <code>{1}</code> unfilled, or an apostrophe disappears", "MessageFormat treats <code>'</code> as a quote character.", "Write <code>''</code> for an apostrophe in a message that has placeholders."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the texts behind it.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>ReminderContractTest</code> ({cnt('ReminderContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>ConcatenatedReminderTrapTest</code> ({cnt('ConcatenatedReminderTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "Bundles complete, rupee formatting, language matching", f"<code>MessagesTest</code> ({cnt('MessagesTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "ConcatenatedReminderTrapTest.java", "<p>Written first: the old fragments, Java's own en-IN format, and the real Hindi sentence.</p>"),
    (T + "ReminderContractTest.java", "<p>Which language wins, the fallback, the server's locale, and every refusal.</p>"),
    (T + "MessagesTest.java", "<p>No Spring: every key in both bundles with the same placeholders, a table of amounts, and the matching rules.</p>"),
    (T + "ApiTest.java", "<p>Shared setup and the two expected sentences for Asha.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/mediqo/reminders/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=MarathiChallengeTest</code>.</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Add Marathi", "Beginner-friendly", 20,
    "Mediqo opens a clinic in Pune. Add Marathi (<code>mr</code>): a bundle with every key and the same placeholders, chosen by <code>?lang=mr</code> or a Marathi <code>Accept-Language</code>.",
    "both tests in <code>MarathiChallengeTest</code> pass.",
    ["A new file <code>messages_mr.properties</code> next to the others, saved as UTF-8.",
     "Spring finds the file on its own; the controller only needs to know Marathi is supported."],
    "challenge/MarathiChallengeTest.java", ["challenge/solution/messages_mr.properties", "challenge/solution/ReminderController.java"]) + challenge(2, "Today, tomorrow, or in N days", "Go deeper", 35,
    "Add a <code>when</code> field: \"today\", \"tomorrow\" or \"in 5 days\" (Hindi: आज, कल, 5 दिन में), from one message per language, not from <code>if</code>/<code>else</code> in Java. Count days in India's time zone from a <code>Clock</code> bean.",
    "both tests in <code>WhenChallengeTest</code> pass, and the station's tests still pass.",
    ["MessageFormat's choice format: <code>{0,choice,0#today|1#tomorrow|1&lt;in {0} days}</code>.",
     "<code>LocalDate.now(clock.withZone(ZoneId.of(\"Asia/Kolkata\")))</code>: at 20:00 UTC on the 19th it is already the 20th in India."],
    "challenge/WhenChallengeTest.java", ["challenge/solution/ReminderController.java", "challenge/solution/RemindersApplication.java",
                                         "challenge/solution/messages.properties", "challenge/solution/messages_hi.properties"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Translations as part of the release</h2>
<p>Mediqo will support ten languages, and product changes the English text every month. Who translates, how does a new key reach the translators, and what stops a release that has an English sentence but no Tamil one? Decide whether a missing translation should fail the build or fall back to English, and how you would see in production how often patients get a fallback.</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the old reminder, and Java's three-digit grouping.</li>
<li>Write the bundles as whole sentences, and a test that keeps them complete.</li>
<li>Choose the language with <code>Locale.lookup</code>; format the date and amount for it.</li>
<li>Turn off the fallback to the server's locale, and test it with the server's locale set to Hindi.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Whole sentences in bundles, with placeholders", "A translator per language; a test that keys stay in step.", '<span class="pill ok">Chosen</span>'],
    ["Translated fragments joined in code", "Word order is English in every language.", '<span class="pill bad">The trap</span>'],
    ["<code>NumberFormat</code> for <code>en-IN</code>", "₹123,456.50: grouped in threes.", '<span class="pill bad">Wrong for lakhs</span>'],
    ["ICU4J for numbers, plurals and dates", "A large dependency; correct for many more locales and plural rules.", '<span class="pill warn">When languages grow</span>'],
    ["Spring's <code>LocaleResolver</code>", "Reads <code>Accept-Language</code> for every request; here the patient's preference also matters, so the choice is explicit.", '<span class="pill warn">For simpler cases</span>'],
    ["Texts in a database table", "Translators can edit without a release; needs its own completeness checks.", '<span class="pill warn">Later</span>']]) + """
<h2>Database design</h2>
<p>None in this station. If texts move to a table: <code>message_text(key, language, text)</code> with a primary key on <code>(key, language)</code>, and a check before release that every key has a row for every supported language.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Translation quality</dt><dd>Texts in a health product are reviewed by a native speaker, and ideally by someone medical. The Hindi here is demo text.</dd>
<dt>SMS length</dt><dd>Hindi in an SMS uses Unicode encoding: 70 characters fit in one message instead of 160, so a long reminder is sent as several parts.</dd>
<dt>Server locale</dt><dd>Containers often run with <code>C</code> or <code>en_US</code>; developers' laptops may not. With <code>fallback-to-system-locale: false</code>, the fallback does not change between them.</dd>
<dt>Missing translations</dt><dd><code>requestedLanguage</code> next to <code>language</code> lets a dashboard count fallbacks per language, which says which translation to add next.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Why not concatenate translated words?", "Languages differ in word order, endings and agreement. Translators need the whole sentence with placeholders, and decide where each value goes."),
    ("How does Spring pick a message for a locale?", "MessageSource looks for the most specific bundle (messages_hi_IN, then messages_hi), then the default messages.properties. With fallbackToSystemLocale on, it tries the server's locale before the default."),
    ("How do you read Accept-Language correctly?", "Parse it into weighted ranges (Locale.LanguageRange.parse) and match against the supported list (Locale.lookup or Locale.filter). Treat a malformed header as no preference."),
    ("Why doesn't NumberFormat for en-IN give lakh grouping?", "DecimalFormat supports a single grouping size, so it groups in threes. ICU4J or a small custom formatter is needed for 1,23,456."),
    ("How do you keep translations complete?", "A test that every key in the default bundle exists in every other bundle with the same placeholders, run on every build."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You added a language and its test caught a missing key."],
    ["Messages", "Whole sentences with placeholders.", "Plural or choice formats instead of <code>if</code>/<code>else</code>."],
    ["Locales", "Accept-Language with weights.", "Why the server's own locale must not decide the fallback."],
    ["Explanation", "Why <code>₹123,456.50</code> is wrong for India.", "When to reach for ICU4J."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any user-facing text:</p>
<ul class="rules">
<li>Is every sentence one message, or is it assembled from pieces?</li>
<li>Are dates, numbers and money formatted for the reader's locale?</li>
<li>What language does a user get when we lack theirs, and does it depend on the server?</li>
<li>Does a test fail when a translation is missing?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
