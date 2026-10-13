"""Station 007 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 7,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · Spring Security 7 · HtmlUtils · MockMvc",
    "simulation": "Two posts and four demo users are fixed in the code; comments live in memory. The attack payloads are harmless test strings: nothing here attacks a real site.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/chaupal/comments/"
T = "src/test/java/com/chaupal/comments/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("XSS (cross-site scripting)", "An attacker's text is shown on a page as code, so it runs in every reader's browser.", "A notice on a board that, when read aloud, makes the reader hand over their keys.", "A comment containing <code>&lt;img onerror=…&gt;</code>."),
    ("Output encoding", "Turning special characters into safe versions for the place they are shown: <code>&lt;</code> becomes <code>&amp;lt;</code> in HTML.", "Writing a quote in a letter inside quotation marks, so nobody mistakes it for your own words.", "<code>HtmlUtils.htmlEscape</code> in <code>CommentHtml</code>."),
    ("Input filter (blocklist)", "Removing \"bad\" things from input before saving.", "A guard who stops anyone named \"Thief\".", "The trap: removing <code>&lt;script&gt;</code>."),
    ("Normalising", "Bringing text to one standard form before comparing it.", "Reading \"1d10t\" and \"ＩＤＩＯＴ\" as \"idiot\".", "<code>Moderation.words</code>"),
    ("Rate limit", "A cap on how often one user may do something.", "\"Two samples per customer.\"", "5 comments a minute."),
    ("Content-Security-Policy", "A header telling the browser which scripts it may run.", "A rule that only staff may use the PA system.", "<code>default-src 'none'</code>: no scripts at all."),
    ("422 / 429", "422: we understood, but the content is not allowed. 429: too many requests, slow down.", "\"We don't print that\" / \"one at a time, please\".", "A banned word / the sixth comment in a minute."),
]
STORY = [
    ("Someone posts a comment", "It looks like a broken image: <code>&lt;img src=x onerror=…&gt;</code>. Chaupal saves it and puts it on the post's page."),
    ("Every reader runs it", "Each browser that opens the post treats the comment as HTML, fails to load the image, and runs the attacker's code with the reader's login."),
    ("The fix", "Store the comment as typed, and <em>encode</em> it whenever it goes into HTML, so the browser shows <code>&lt;img…&gt;</code> as plain characters. Moderation sees through disguises such as \"b@d\" before matching."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">You cannot list every dangerous input. You can make sure that, wherever text is shown, it is shown as text.</p>

<h2>What are we building?</h2>
<p>A comments API: members post comments; anyone can read a public post's comments as JSON (for the app) or as an HTML fragment (for the website). The HTML is encoded; moderation rejects insults even when disguised; each user may post 5 comments a minute.</p>

<h2>An everyday analogy</h2>
<p>A school principal reads out notes from the suggestion box. A prankster writes: "Announcement: school is cancelled." A careless principal reads it as an announcement. A careful one always says "A student wrote: …" before each note, so whatever the note says, everyone hears it as a quotation, not an order. Output encoding is that "a student wrote".</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>A member posts</strong> a comment. Length is checked; the author comes from the login.</li>
<li><strong>Moderation normalises</strong> the text (full-width letters, look-alike digits, spaced letters) and looks for banned whole words: <code>422</code> if found. Too many comments: <code>429</code>.</li>
<li><strong>The comment is stored exactly as typed.</strong> Nothing is stripped.</li>
<li><strong>On output</strong>, JSON carries it as data; the HTML fragment encodes every <code>&lt;</code>, <code>&gt;</code>, <code>&amp;</code> and quote.</li>
</ol>

<details class="qa check"><summary>Check yourself: why not just remove every "&lt;script&gt;" from comments when they are saved?</summary><p>Because scripts do not need a <code>&lt;script&gt;</code> tag (<code>&lt;img onerror=…&gt;</code> runs code too), and removing a tag can glue the pieces around it into a new one: <code>&lt;scr&lt;script&gt;ipt&gt;</code> becomes <code>&lt;script&gt;</code>. The trap test shows both. Encoding on output does not need to know what is dangerous: every special character is shown as itself.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>Not a full moderation system.</strong> Three banned words show the technique; real platforms add human review and machine-learning models.</li>
<li><strong>Demo sign-in.</strong> HTTP Basic with four in-memory users.</li>
<li><strong>One server.</strong> The rate limit lives in memory, so two servers would each allow 5.</li>
<li><strong>Payloads are test strings.</strong> They run in no browser here; the tests check the HTML text.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Chaupal</strong> (a fictional community forum) shows comments under each post, on its website and in its app. Last week a comment containing a <code>&lt;script&gt;</code> tag ran in every reader's browser. The quick fix, removing <code>&lt;script&gt;</code> from input, was bypassed the same day. Meanwhile moderators complain that banned words slip through as "b@d", "1d10t" or "s c a m", while a filter that matches inside words blocked a restaurant review that mentioned "scampi".</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> any comment, <b>when</b> it is shown in the HTML fragment, <b>then</b> every <code>&lt;</code> <code>&gt;</code> <code>&amp;</code> <code>"</code> <code>'</code> from the user is encoded, and the response has a Content-Security-Policy that allows no scripts.</li>
<li><b>Given</b> any comment, <b>then</b> the JSON returns it exactly as typed.</li>
<li><b>Given</b> a banned word, even as "ＩＤＩＯＴ", "1d10t" or "s c a m", <b>then</b> <code>422</code> without repeating the word. <b>Given</b> "scampi", <b>then</b> it is accepted.</li>
<li><b>Given</b> a sixth comment within 60 seconds from one user, <b>then</b> <code>429</code> with <code>Retry-After</code>.</li>
<li><b>Given</b> no login, <b>then</b> posting is <code>401</code>; <b>given</b> a muted user, <b>then</b> <code>403</code>; <b>given</b> another user's private post, <b>then</b> <code>404</code> for reading and posting.</li>
<li><b>Given</b> a blank or 501-character comment, <b>then</b> <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Validate input (length, required); encode output (for HTML). Never strip or rewrite what users type.</li>
<li>Moderation compares whole normalised words with <code>Locale.ROOT</code>.</li>
<li>At most 5 comments per user per 60 seconds (a demo rule).</li>
<li>The author is the signed-in user. Errors are RFC 9457 problems that never repeat the input.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Explain XSS and why output encoding beats input filtering.</li>
<li>Encode text for HTML with <code>HtmlUtils.htmlEscape</code>, at the point of output.</li>
<li>Normalise text (Unicode NFKC, case, look-alikes, spacing) before matching.</li>
<li>Limit input length and rate, with <code>400</code>, <code>422</code> and <code>429</code>.</li>
<li>Add a Content-Security-Policy as a second line of defence.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Who", "Purpose"], [
    ["<code>POST</code>", "<code>/posts/{postId}/comments</code>", "Members", "Add a comment. Body: <code>{\"text\": \"…\"}</code>, 1–500 characters."],
    ["<code>GET</code>", "<code>/posts/{postId}/comments</code>", "Anyone (private posts: their author)", "<code>Accept: application/json</code> (default): the comments as data. <code>Accept: text/html</code>: an encoded HTML fragment."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "Type (after <code>…/problems/</code>)", "When"], [
    ['<span class="pill ok">201</span>', "", "Comment saved"],
    ['<span class="pill ok">200</span>', "", "Comments listed"],
    ['<span class="pill warn">400</span>', "<code>invalid-request</code>", "Blank, over 500 characters, broken JSON"],
    ['<span class="pill warn">401</span>', "<code>unauthenticated</code>", "Posting without signing in"],
    ['<span class="pill warn">403</span>', "<code>forbidden</code>", "A muted user posting"],
    ['<span class="pill warn">404</span>', "<code>post-not-found</code>", "Unknown post, or someone else's private post"],
    ['<span class="pill warn">422</span>', "<code>community-rules</code>", "A banned word, disguised or not"],
    ['<span class="pill warn">429</span>', "<code>too-many-comments</code>", "A sixth comment within 60 seconds; <code>Retry-After: 60</code>"]]) + """
<p class="note"><strong>JSON is data, not HTML.</strong> The JSON list returns <code>&lt;img…&gt;</code> exactly as typed, which is correct: JSON is not run by a browser. The app must put it on screen as text (for example <code>textContent</code> in a web page, never <code>innerHTML</code>). Encoding belongs to whoever writes the HTML.</p>
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out. The <code>Authorization</code> header carries demo passwords.</p>
""" + examples([
    ("01-comment", "Case 1: Ravi comments", "<b>Why:</b> valid text from a member: <code>201</code>, with Ravi as the author because he signed in as Ravi."),
    ("02-attack", "Case 2: Kabir posts an attack", "<b>Why:</b> it is just text and breaks no rule, so it is saved exactly as typed. Its safety comes at output, in case 3."),
    ("03-html", "Case 3: the website asks for HTML", "<b>Why:</b> the attack arrives as <code>&amp;lt;img…&amp;gt;</code>: the browser would show the characters and run nothing. The Content-Security-Policy header forbids scripts anyway."),
    ("04-json", "Case 4: the app asks for JSON", "<b>Why:</b> the same comments as data, text unchanged. The app shows it as text."),
    ("05-disguised-insult", "Case 5: \"1d10t\"", "<b>Why:</b> normalised to \"idiot\", a banned word: <code>422</code>. The answer does not repeat the word."),
    ("06-scampi", "Case 6: scampi", "<b>Why:</b> whole words are compared, and \"scampi\" is not \"scam\": <code>201</code>."),
    ("07-muted", "Case 7: a muted user", "<b>Why:</b> Tara is signed in but muted: <code>403</code>."),
    ("08-private-post", "Case 8: Asha opens Ravi's private post", "<b>Why:</b> <code>404</code>, as for a post that does not exist."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What the API does", "Proved by"], [
    ["Seven common XSS payloads (script, upper-case script, nested, img, svg, iframe, javascript: link)", "Stored as typed; shown in HTML as exactly <code>htmlEscape(payload)</code>", "<code>everyPayloadIsStoredAsTextAndShownAsText</code> (7 cases)"],
    ["<code>&lt;b&gt;</code>, <code>&amp;</code>, double and single quotes", "All encoded; CSP header present", "<code>theHtmlFragmentEncodesEveryCharacterThatMatters</code>"],
    ["JSON list", "Oldest first, text unchanged", "<code>jsonListsCommentsOldestFirstWithTheTextExactlyAsTyped</code>"],
    ["\"ＩＤＩＯＴ\", \"1d10t\", \"$c@m\", \"s c a m\", \"stuuupid\", \"id-iot\"", "Caught", "<code>disguisesAreSeenThrough</code>, <code>aBannedWordIs422WithoutRepeatingIt</code>"],
    ["\"scampi\", \"smart idea\"", "Allowed", "<code>wholeWordsOnlySoScampiIsFine</code>"],
    ["\"stupidity\", \"st*pid\"", "Allowed: known limits of a word list", "<code>theLimitsOfAWordList</code>"],
    ["Turkish server locale", "Still caught", "<code>aTurkishServerLocaleChangesNothing</code>"],
    ["Blank, 501 characters; exactly 500", "<code>400</code>; <code>201</code>", "<code>blankOrTooLongTextIs400</code>"],
    ["Sixth comment in a minute", "<code>429</code> + <code>Retry-After</code>; other users unaffected", "<code>theSixthCommentInAMinuteIs429WithRetryAfter</code>"],
    ["No login; muted user", "<code>401</code>; <code>403</code>", "<code>postingWithoutSigningInIs401</code>, <code>aMutedUserCanReadButNotPost403</code>"],
    ["Another user's private post", "<code>404</code> to read or post", "<code>anotherUsersPrivatePostLooksLikeItDoesNotExist</code>"],
    ["<code>author</code> in the body", "Ignored", "<code>anAuthorFieldInTheBodyIsIgnored</code>"],
    ["Refused payload", "Not echoed in the error", "<code>aRefusedPayloadIsNotEchoedInTheError</code>"],
    ["Unknown post; broken JSON", "<code>404</code>; <code>400</code>", "<code>anUnknownPostIs404</code>, <code>brokenJsonIs400</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Filtering <code>&lt;script&gt;</code> from input instead of encoding output; attackers bypass the filter.</p>
<p>A "before" controller removes <code>&lt;script&gt;</code> and <code>&lt;/script&gt;</code> from every comment, then builds HTML by gluing strings. The first test posts two classic payloads: the <code>&lt;img onerror&gt;</code> passes untouched, and <code>&lt;scr&lt;script&gt;ipt&gt;</code> becomes a working <code>&lt;script&gt;</code> <em>because of</em> the filter. The second test sends the same payloads to the real API: both come out as harmless text.</p>
</div>
""" + code(read(T + "InputFilterTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "SecurityConfig.java", dwn("Lets anyone read, members post, muted users only read; adds the Content-Security-Policy header.",
        "Access rules live in one place, and CSP is a second wall if encoding is ever missed.",
        "Anyone could post; a single missed <code>htmlEscape</code> would run scripts.")),
    (J + "CommentController.java", dwn("One <code>POST</code>, and one <code>GET</code> URL with two formats chosen by <code>Accept</code>: JSON or HTML.",
        "The same data, two outputs: each output is responsible for its own safety.",
        "No API.",
        "<ul><li><code>produces</code> on each <code>@GetMapping</code> lets Spring pick by the request's <code>Accept</code> header.</li></ul>")),
    (J + "CommentRequest.java", dwn("Validates input: required and at most 500 characters. No author field.", "Validation checks what input <em>is</em>, not whether it looks dangerous.", "Empty or huge comments.")),
    (J + "CommentService.java", dwn("Checks the post is visible, runs moderation and the rate limit, stores the text exactly as typed.",
        "Storing the original keeps every output free to encode for its own format (HTML, JSON, CSV, an email).",
        "Rules spread around; a filtered copy that is neither the original nor safe."),),
    (J + "Moderation.java", dwn("Normalises text step by step, then compares whole words with a small list.",
        "Disguises are undone before matching; whole words avoid blocking \"scampi\".",
        "\"1d10t\" passes and \"scampi\" is blocked (see Review).",
        "<ul><li>NFKC turns full-width <code>ＩＤＩＯＴ</code> into <code>IDIOT</code>.</li><li>Runs of one-letter words are joined: <code>s c a m</code>.</li><li>Three or more repeats collapse: <code>stuuupid</code>.</li></ul>")),
    (J + "RateLimiter.java", dwn("Keeps each user's recent comment times and refuses a sixth within 60 seconds.", "Limits the damage of spam bots and angry bursts.", "One account can flood a post.")),
    (J + "CommentHtml.java", dwn("Builds the HTML fragment, passing every piece of user text through <code>htmlEscape</code>.",
        "This is the one place where text becomes HTML, so it is the one place that must encode.",
        "The attack in case 2 runs in every reader's browser.")),
    (J + "ApiErrors.java", "<p>The problem shape from station 006: 404, 422, 429 with <code>Retry-After</code>, and validation errors that never repeat input.</p>"),
    (J + "ProblemResponses.java", "<p>401 and 403 in the same problem shape (from station 006).</p>"),
    (J + "Post.java", "<p>A post and who may see it.</p>"),
    (J + "Comment.java", "<p>A stored comment.</p>"),
    (J + "Exceptions.java", "<p>Post not found, community rules, too many comments.</p>"),
]
tree = """stations/007-comment-moderation-and-xss-safe-output/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/chaupal/comments/
│   ├── SecurityConfig.java   ├── CommentController.java   ├── CommentRequest.java
│   ├── CommentService.java   ├── Moderation.java          ├── RateLimiter.java
│   ├── CommentHtml.java      ├── ApiErrors.java           ├── ProblemResponses.java
│   └── Post.java, Comment.java, Exceptions.java, CommentsApplication.java
├── src/test/java/com/chaupal/comments/   (see Tests)
├── review/                   the flawed version (see Review)
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
<p>Demo users: <code>asha</code>, <code>ravi</code>, <code>kabir</code> (members) and <code>tara</code> (muted); each password is the name plus <code>-demo-pass</code>. The attack body is in <code>docs/attack.json</code>.</p>
""" + code("""# Post the attack: expect 201
curl -i -u kabir:kabir-demo-pass -X POST http://localhost:8080/posts/1/comments -H "Content-Type: application/json" -d "@docs/attack.json"

# See it as HTML: expect &lt;img ... &gt; and a Content-Security-Policy header
curl -i -H "Accept: text/html" http://localhost:8080/posts/1/comments""", "bash") + """
<p>Save the HTML answer as <code>comments.html</code> and open it in a browser: you see the attack as text, and no alert appears.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["JSON when you wanted HTML", "No <code>Accept: text/html</code> header.", "Add <code>-H \"Accept: text/html\"</code>."],
    ["<code>429</code>", "More than 5 comments in a minute as one user.", "Wait 60 seconds or use another demo user."],
    ["<code>release version 25 not supported</code>", "Maven is using an older JDK.", "Point <code>JAVA_HOME</code> at JDK 25, or add <code>-Djava.version=21</code>."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels: security filters, controller, service, and the HTML on the way out.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "Required tests come from the station's types. The validator fails a station that is missing any of them.") + """
<h2>Required tests for this station</h2>
<p>Station type: <span class="chip">Security</span></p>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>CommentContractTest</code> ({cnt('CommentContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>InputFilterTrapTest</code> ({cnt('InputFilterTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Security", "401, 403, another user's data, malicious input", f"<code>CommentSecurityTest</code> ({cnt('CommentSecurityTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "Normalising and matching on its own", f"<code>ModerationTest</code> ({cnt('ModerationTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1, Spring Security 7. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "InputFilterTrapTest.java", "<p>Written first: the input filter misses one payload and builds another.</p>"),
    (T + "CommentSecurityTest.java", "<p>401, 403, private posts, the author field, seven payloads, and no echo in errors.</p>"),
    (T + "CommentContractTest.java", "<p>Post, JSON, HTML with CSP, length, moderation, rate limit, 404, broken JSON.</p>"),
    (T + "ModerationTest.java", "<p>Disguises caught, innocent words left alone, the honest limits, and a Turkish locale.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: no comments and a fresh rate limit before each test; bodies built by Jackson so payloads arrive exactly.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/chaupal/comments/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=BoldFormattingChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Safe bold text", "Go deeper", 30,
    "Members want <code>**bold**</code>. In the HTML fragment, turn <code>**text**</code> into <code>&lt;strong&gt;text&lt;/strong&gt;</code>, while every other tag the user typed stays encoded, including one inside the stars.",
    "all four tests in <code>BoldFormattingChallengeTest</code> pass, and the station's tests still pass.",
    ["Order matters: encode first, then format. After encoding, the only tag in the text can be the one you add.",
     "<code>*</code> is not changed by HTML encoding, so the stars are still there to find.",
     "A regular expression with a lazy group, <code>\\*\\*(…*?)\\*\\*</code>, finds each pair."],
    "challenge/BoldFormattingChallengeTest.java", ["challenge/solution/CommentHtml.java"]) + challenge(2, "Report a comment", "Go deeper", 40,
    "Add <code>POST /posts/{postId}/comments/{commentId}/reports</code> for members: <code>204</code> each time. When 3 different members have reported a comment, it is hidden from both lists. Reporting twice counts once; an unknown comment or an invisible post is <code>404</code>; muted users get <code>403</code>.",
    "all four tests in <code>ReportChallengeTest</code> pass.",
    ["A <code>Set</code> of reporters per comment makes \"twice counts once\" automatic.",
     "Hide in <code>list()</code>, so JSON and HTML agree.",
     "Always <code>204</code>: telling a reporter \"that was the third report\" helps people coordinate to hide comments they dislike."],
    "challenge/ReportChallengeTest.java", ["challenge/solution/CommentService.java", "challenge/solution/CommentController.java", "challenge/solution/SecurityConfig.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Links in comments</h2>
<p>Members want links to be clickable. Which URLs would you allow (think of <code>javascript:</code> and <code>data:</code>)? Where in the encode-then-format order does linking happen? Which attributes would you add to the <code>&lt;a&gt;</code> tag, and why? When would you use a tested HTML sanitiser library instead of your own rules?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the input filter misses <code>&lt;img onerror&gt;</code> and builds a <code>&lt;script&gt;</code>.</li>
<li>Store text as typed; encode in the one place that writes HTML.</li>
<li>Add CSP as a second wall.</li>
<li>Write <code>Moderation.words</code> step by step, with a test per disguise and per innocent word.</li>
<li>Add length and rate limits, each with its own status code.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Store as typed, encode on output", "Every output path must encode for its own format.", '<span class="pill ok">Chosen</span>'],
    ["Blocklist filter on input", "Bypassed by other tags, case tricks and nesting; damages honest text.", '<span class="pill bad">Wrong</span>'],
    ["HTML-encode on input, store encoded", "JSON and CSV now show <code>&amp;lt;</code>; encoding twice shows <code>&amp;amp;lt;</code>.", '<span class="pill bad">Wrong</span>'],
    ["A sanitiser library allowing some tags (OWASP Java HTML Sanitizer)", "The right choice when users need real formatting. A dependency to keep updated.", '<span class="pill warn">When needed</span>'],
    ["Substring match for banned words", "Blocks \"scampi\"; misses \"1d10t\".", '<span class="pill bad">Wrong</span>'],
    ["Hold suspicious comments for a moderator", "Kinder than rejecting, slower to appear.", '<span class="pill warn">Common in production</span>']]) + """
<h2>Database design</h2>
<p>None in this station. With a database, store the original text in a <code>TEXT</code> column with a length check, and never store an "encoded" copy.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Security</dt><dd>Encoding stops HTML injection; CSP stops scripts even if encoding is missed; JSON clients must render text as text. Encoding is per context: HTML text, an HTML attribute, a URL and JavaScript each need their own.</dd>
<dt>Abuse</dt><dd>Moderation runs before the rate limit, so refused comments do not use up a user's 5; a determined spammer of banned words is limited only by the 422. Watch the 422 rate per user.</dd>
<dt>Scale</dt><dd>The rate limit is per server. Several servers need a shared counter (Redis or a gateway), covered in later stations.</dd>
<dt>Maintainability</dt><dd>The banned list is code here; in production it is data that moderators can edit, with tests for both "caught" and "allowed".</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is XSS, in one sentence?", "An attacker gets their text into a page in a way that the browser runs it as code, with the reader's session."),
    ("Why encode output instead of filtering input?", "A filter must know every dangerous input and fails on the one it missed; encoding needs no list: every special character is shown as itself. Filters also corrupt honest text."),
    ("Is JSON safe from XSS?", "JSON itself is data. The danger is the client: inserting JSON text with innerHTML brings XSS back. Use textContent or a framework's default escaping."),
    ("What does a Content-Security-Policy add?", "A second line of defence: the browser refuses to run scripts the policy does not allow, even if an attacker gets markup into the page."),
    ("Why normalise text before matching banned words?", "Attackers use look-alikes: full-width letters, digits for letters, spaces between letters. Normalising maps them to one form so one list covers them; whole-word comparison avoids blocking innocent words."),
    ("422 or 400 for a banned word?", "400 is for malformed requests. The request is well-formed; its content is not acceptable. 422 says exactly that."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can predict what the flawed version fails."],
    ["Security", "Every output of user text is encoded.", "You can name the encoding for an attribute, a URL and JavaScript."],
    ["Design", "Store as typed, encode on output.", "You can explain why encode-then-format, not the reverse."],
    ["Explanation", "You can show the nested-tag bypass.", "You can explain the limits of any word list."]])

# ---------- Level 3: Review ----------
FLAWED = run("review-run.txt")[0]
findings = [
    ("\"Sanitise on input\" with a <code>&lt;script&gt;</code> regex", "Only script tags are removed; <code>&lt;img onerror&gt;</code>, <code>&lt;svg onload&gt;</code> and others pass. It also damages honest comments: <code>&lt;scr&lt;script&gt;ipt&gt;…</code> was stored as <code>&lt;scr</code>.", "<code>everyPayloadIsStoredAsTextAndShownAsText</code>: the stored text differs from what was sent."),
    ("No encoding in <code>CommentHtml</code>", "\"Already sanitised\" is trusted, so every payload the filter missed reaches the page as live HTML.", "<code>encodingOnOutputTurnsBothIntoHarmlessText</code>, <code>theHtmlFragmentEncodesEveryCharacterThatMatters</code> and the payload cases."),
    ("Substring matching in <code>Moderation</code>", "<code>text.toLowerCase().contains(word)</code> misses \"1d10t\" and \"ＩＤＩＯＴ\", blocks \"scampi\", and uses the server's locale.", "<code>aBannedWordIs422WithoutRepeatingIt</code> (got 201), all five <code>ModerationTest</code> tests."),
    ("Private posts readable by anyone", "<code>list()</code> checks only that the post exists, not that the reader may see it. Posting is still blocked, which makes the gap easy to miss.", "<code>anotherUsersPrivatePostLooksLikeItDoesNotExist</code>: 200 instead of 404."),
]
review = belongs(["18. Reviewer view: a flawed version to find and fix, with the reasoning"],
                 "Real code review practice. The flawed version is run against the same tests, and the real failures are shown.") + """
<h2>The pull request</h2>
<p>A teammate's "security hardening" PR: sanitise on the way in, a simpler moderator, and a tidy-up of <code>list()</code>. Read the three files and list every problem before opening the findings.</p>
<p class="path">review/CommentService.java</p>
""" + code(read("review/CommentService.java"), "java") + """
<p class="path">review/CommentHtml.java</p>
""" + code(read("review/CommentHtml.java"), "java") + """
<p class="path">review/Moderation.java</p>
""" + code(read("review/Moderation.java"), "java") + """
<h2>Findings</h2>
""" + "".join(f'<details class="finding"><summary><span class="sev">{i}</span>{t}</summary><p>{why}</p><p class="evidence"><b>Test evidence:</b> {ev}</p></details>'
             for i, (t, why, ev) in enumerate(findings, 1)) + """
<h2>Same tests, flawed version</h2>
<p class="muted">From <code>docs/review-run.txt</code>: the three flawed files copied over the real ones, then the full suite run.</p>
""" + table(["Test class", "Fixed version", "Flawed version"], [
    [f"<code>{c}</code>", f'<span class="pill ok">{SP[c][0]} / {SP[c][1]}</span>',
     f'<span class="pill {"ok" if FLAWED[c][0] == FLAWED[c][1] else "bad"}">{FLAWED[c][0]} / {FLAWED[c][1]}</span>']
    for c in sorted(SP, key=lambda c: (FLAWED[c][0] < FLAWED[c][1], c))]) + """
<p class="note">The PR's own description says "security hardening". Every change made the API less safe. Reviews need tests that ask what an attacker would send, not just whether the happy path still works.</p>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
