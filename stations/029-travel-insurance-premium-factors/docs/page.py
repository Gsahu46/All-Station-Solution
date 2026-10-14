"""Station 029 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 29,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · List<T> injection · @Order · @Qualifier · @Primary · @PostConstruct · MockMvc",
    "simulation": "A quote only: no policy is issued and nothing is charged. The rates are demo numbers, not a real insurer's, and taxes are not included.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/bimaly/premiums/"
T = "src/test/java/com/bimaly/premiums/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Premium", "What a traveller pays for the policy.", "₹1,839 for 10 days in Europe.", "<code>premiumPaise</code>"),
    ("Factor", "One step that changes the premium: a rate, a multiplier or an add-on.", "Age, destination, adventure sports.", "<code>PremiumFactor</code>"),
    ("Bean", "An object Spring creates and hands to whoever needs it.", "A tool in a shared workshop, given to whoever asks.", "Each factor is a bean"),
    ("List injection", "Asking Spring for every bean of a type, as a list.", "Asking for \"all the checklists\", not one.", "<code>List&lt;PremiumFactor&gt;</code>"),
    ("@Order", "The position of a bean in such a list.", "Step numbers on a recipe.", "<code>@Order(30)</code> on <code>Age</code>"),
    ("@Qualifier and @Primary", "Picking one bean when there are several: by name, or the default.", "\"The red pen\" versus \"a pen\".", "Two <code>Rounding</code> beans"),
]
STORY = [
    ("One giant premium class", "Every new risk (a new destination, a new age band, adventure sports) means editing the same 400-line class. Every edit risks every price."),
    ("A first split goes wrong", "Factors become separate beans, but the quote service asks for one <code>PremiumFactor</code>. The app will not start; someone adds <code>@Primary</code>, and it starts, quoting with one factor. Then the order of the factors depends on how classes were scanned, and the adventure loading gets multiplied by age: ₹400 too much."),
    ("The fix", "Inject all factors as a list, in an explicit order, and refuse to start if two share an order."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">When several beans do one job together, ask for all of them, and say their order out loud.</p>

<h2>What are we building?</h2>
<p><code>POST /premium-quotes</code> prices a trip by running every premium factor in order, and returns the premium with a breakdown of each step.</p>

<h2>An everyday analogy</h2>
<p>A recipe: dough, then filling, then oven, then glaze. Each step is separate and numbered. Swap the oven and the glaze and you get a different dish, from the same ingredients.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>At startup</strong>, Spring collects every <code>PremiumFactor</code> bean, sorted by <code>@Order</code>, and the calculator checks no two share a place.</li>
<li><strong>For each quote</strong>, the running total starts at zero.</li>
<li><strong>Each factor</strong> takes the total and returns a new one, with a line for the breakdown.</li>
<li><strong>Finally</strong>, the premium is rounded up to the rupee (the insurer's rule) and the per-day figure to the nearest rupee.</li>
</ol>

<details class="qa check"><summary>Check yourself: the adventure add-on is ₹50 a day. Why does it matter whether it comes before or after the age multiplier?</summary><p>After, it stays ₹50 a day. Before, it is multiplied too: ×1.8 for a 67-year-old, ₹90 a day. Same factors, different price, so the order is part of the rule.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>Not real insurance pricing.</strong> Demo rates; real pricing is regulated and actuarial.</li>
<li><strong>No policy.</strong> A quote only.</li>
<li><strong>No taxes.</strong> The premium shown excludes them.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Bimaly</strong> (a fictional insurance app) adds risk factors often. In one class, each change risks every price; split carelessly into beans, the app either fails to start, quotes with one factor, or applies factors in whatever order classes happen to load.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> age 67, Europe, 10 days, adventure sports, <b>then</b> ₹1,838.75 before rounding, charged as ₹1,839, with base, destination, age, adventure and minimum in that order.</li>
<li><b>Given</b> age 25, Asia, 3 days, <b>then</b> the ₹199 minimum.</li>
<li><b>Given</b> age 45, Europe, 5 days, <b>then</b> ₹483.44 is charged as ₹484: rounded up, never to the nearest.</li>
<li><b>Given</b> age 81, <b>then</b> <code>422</code>: online quotes go up to 80 (a demo rule).</li>
<li><b>Given</b> an unknown destination, days outside 1 to 180, or no age, <b>then</b> <code>400</code>.</li>
<li><b>Given</b> two factors with the same <code>@Order</code>, or one with none, <b>then</b> the app does not start.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Demo rates: ₹42.50 a day; destination ×1.00 to ×3.00; age ×0.80 to ×2.50; adventure +₹50 a day, not multiplied; minimum ₹199.</li>
<li>Each step rounds to the paisa; the premium rounds up to the rupee; the per-day figure to the nearest rupee.</li>
<li>Factors are stateless singletons; a new factor is a new bean with an <code>@Order</code>.</li>
<li><code>adventureSports</code> is optional (false when missing).</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Inject several beans of one type as a <code>List</code>, in a defined order.</li>
<li>Choose one bean among several with <code>@Qualifier</code>, and a default with <code>@Primary</code>.</li>
<li>Know why factors must be stateless singletons.</li>
<li>Use a lifecycle callback (<code>@PostConstruct</code>) to fail fast at startup.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>POST</code>", "<code>/premium-quotes</code>", "A premium with its step-by-step breakdown."]]) + """
<h2>Request body</h2>
""" + table(["Field", "Rule"], [
    ["<code>age</code>", "0 to 120; above 80 is <code>422</code>."],
    ["<code>destination</code>", "<code>ASIA</code>, <code>EUROPE</code>, <code>USA_CANADA</code> or <code>WORLDWIDE</code>."],
    ["<code>days</code>", "1 to 180."],
    ["<code>adventureSports</code>", "Optional, default false."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "A quote"],
    ['<span class="pill warn">400</span>', "A field missing, out of range or not one of the values"],
    ['<span class="pill warn">422</span>', "Over 80: no online cover"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-senior-to-europe-with-adventure", "Case 1: 67, Europe, 10 days, adventure sports", "<b>Why:</b> each step in order: base ₹425, Europe ×1.75, age ×1.80, then the adventure add-on, not multiplied. ₹1,838.75 is charged as ₹1,839."),
    ("02-a-short-trip-pays-the-minimum", "Case 2: 25, Asia, 3 days", "<b>Why:</b> ₹127.50 of cover is raised to the ₹199 minimum."),
    ("03-rounded-up-not-to-nearest", "Case 3: 45, Europe, 5 days", "<b>Why:</b> ₹483.44 is charged as ₹484: the qualified rounding bean rounds up. The per-day figure uses the default (nearest)."),
    ("04-over-80", "Case 4: age 81", "<b>Why:</b> <code>422</code>: an agent quotes for older travellers."),
    ("05-a-destination-we-do-not-cover", "Case 5: a destination that does not exist", "<b>Why:</b> not one of the four: <code>400</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["67, Europe, 10 days, adventure", "₹1,839, five steps in order", "<code>aQuoteShowsEveryFactorInOrder</code>"],
    ["25, Asia, 3 days", "₹199 minimum", "<code>aShortCheapTripPaysTheMinimum</code>"],
    ["106,357 and 48,344 paise", "106,400 and 48,400: always up", "<code>paiseAreRoundedUpToTheNextRupee</code>"],
    ["Age 81; age 80", "<code>422</code>; quoted", "<code>travellersOver80Are422</code>"],
    ["MARS; 0 or 181 days; age −1; no age", "<code>400</code>", "<code>badRequestsAre400</code>"],
    ["The injected list", "Base, destination, age, adventure, minimum", "<code>theListComesInOrderOrder</code>"],
    ["The two rounding beans", "Qualified rounds up; primary to nearest", "<code>theQualifiedRoundingRoundsUpAndThePrimaryRoundsToNearest</code>"],
    ["Every factor bean", "A singleton with no per-quote fields", "<code>factorsAreStatelessSingletons</code>"],
    ["Two factors with @Order(30)", "The app does not start", "<code>twoFactorsWithTheSameOrderStopTheAppStarting</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Injecting one bean when several exist, or relying on unspecified bean order.</p>
<p>The first test builds a small context where a service asks for one <code>PremiumFactor</code> among two: it does not start. The second adds <code>@Primary</code> to one, the usual quick fix: it starts, and quotes a free policy, because only the age factor runs. The third applies the same five factors in two orders: ₹1,838.75 against ₹2,238.75. While building, removing <code>@Order</code> from one factor stopped the app (the startup check), moving adventure before age turned 2 tests red, and dropping the <code>@Qualifier</code> from the calculator turned 1 red (₹483 instead of ₹484).</p>
</div>
""" + code(read(T + "FactorOrderTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "PremiumQuoteController.java", dwn("Validates the request and asks the calculator for a quote.",
        "The age limit is a product rule for this channel, so it lives here, not in a factor.",
        "Pricing logic in the controller.")),
    (J + "PremiumCalculator.java", dwn("Runs every factor in order, then rounds.",
        "<code>List&lt;PremiumFactor&gt;</code> from Spring, sorted by <code>@Order</code>; a new factor does not change this class.",
        "The trap: one injected factor, or an order nobody chose.",
        "<ul><li><code>@Qualifier(\"premium\")</code> picks the rounding that charges; the unqualified one is the <code>@Primary</code>.</li><li><code>@PostConstruct</code> checks the orders once, after injection, before any quote.</li></ul>")),
    (J + "Factors.java", dwn("The five factors, each a bean with its <code>@Order</code>.",
        "Small, stateless, independently testable steps.",
        "One class that knows every rate.")),
    (J + "PremiumFactor.java", "<p>The interface every factor implements, and the breakdown step it returns.</p>"),
    (J + "Rounding.java", "<p>Two beans of one type: nearest rupee (<code>@Primary</code>) and up to the rupee (<code>@Qualifier(\"premium\")</code>).</p>"),
    (J + "Trip.java", "<p>What a quote is for.</p>"),
    ("src/main/resources/application.yaml", "<p>Problem bodies for every error.</p>"),
    (J + "PremiumsApplication.java", "<p>Standard Spring Boot entry point.</p>"),
]
tree = """stations/029-travel-insurance-premium-factors/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/bimaly/premiums/
│   ├── PremiumQuoteController.java   ├── PremiumCalculator.java
│   ├── PremiumFactor.java            ├── Factors.java   ├── Rounding.java
│   ├── Trip.java                     └── PremiumsApplication.java
├── src/test/java/com/bimaly/premiums/   (see Tests)
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
<h2>At startup</h2>
<p class="muted">The app's own log line from the run that captured the examples (<code>docs/captures/startup-log.txt</code>): the factors, in the order every quote will use.</p>
<pre class="console">""" + e(read("docs/captures/startup-log.txt")) + """</pre>
<h2>Try it yourself</h2>
""" + code("""curl -X POST http://localhost:8080/premium-quotes -H "Content-Type: application/json" \\
     -d '{"age":67,"destination":"EUROPE","days":10,"adventureSports":true}'""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>NoUniqueBeanDefinitionException</code> at startup", "Something asks for one <code>PremiumFactor</code> or one <code>Rounding</code>.", "Ask for a <code>List</code>, or add <code>@Qualifier</code>."],
    ["<code>Premium factor … shares @Order(…)</code> at startup", "Two factors have the same position.", "Give each a different <code>@Order</code>."],
    ["<code>400</code> for a missing <code>adventureSports</code>", "A primitive <code>boolean</code> in the request record.", "Use <code>Boolean</code>: Jackson 3 refuses a missing primitive."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found (no cover for the age)", f"<code>PremiumQuoteContractTest</code> ({cnt('PremiumQuoteContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>FactorOrderTrapTest</code> ({cnt('FactorOrderTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "Order, qualifier and primary, scopes, the startup check", f"<code>FactorWiringTest</code> ({cnt('FactorWiringTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "FactorOrderTrapTest.java", "<p>Written first: small contexts built with <code>ApplicationContextRunner</code> that fail to start, or start wrong, and the same factors in two orders.</p>"),
    (T + "PremiumQuoteContractTest.java", "<p>Quotes and their breakdowns, looked up by factor name so a new factor does not break them.</p>"),
    (T + "FactorWiringTest.java", "<p>The real context's list order, the two rounding beans, singletons without state, and the duplicate-order check.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/bimaly/premiums/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=NewFactorChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "A new factor, nothing else", "Beginner-friendly", 20,
    "A pre-existing medical condition adds 40% to the cover cost, after age and before the adventure add-on. Add it without editing <code>PremiumCalculator</code>.",
    "the test in <code>NewFactorChallengeTest</code> passes, and the station's tests still pass.",
    ["A new <code>@Component</code> implementing <code>PremiumFactor</code>, with an <code>@Order</code> between 30 and 40.",
     "The request and the trip need the new field; keep the old trip constructor for code that does not know it."],
    "challenge/NewFactorChallengeTest.java", ["challenge/solution/PreExistingCondition.java", "challenge/solution/Trip.java", "challenge/solution/PremiumQuoteController.java"]) + challenge(2, "A campaign you can switch off", "Go deeper", 25,
    "A Diwali campaign takes 10% off before the minimum. The factor exists only while <code>bimaly.campaign.diwali=true</code>; switching it off is a configuration change, not a release.",
    "the test in <code>CampaignDiscountChallengeTest</code> passes.",
    ["<code>@ConditionalOnProperty(\"bimaly.campaign.diwali\")</code> on the factor: no property, no bean.",
     "An <code>@Order</code> below the minimum's 100."],
    "challenge/CampaignDiscountChallengeTest.java", ["challenge/solution/CampaignDiscount.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Factors as configuration</h2>
<p>The actuaries want to change multipliers weekly without a release. Which parts would you move to configuration (the numbers, the bands, the order?) and which stay in code? How would you stop a bad configuration from reaching customers: validation at startup, a preview endpoint, or a second approver?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: one-of-several, the <code>@Primary</code> quick fix, and two orders.</li>
<li>Split the premium into factor beans with explicit <code>@Order</code>.</li>
<li>Inject them as a list; check the orders at startup.</li>
<li>Add the two rounding beans and pick each with <code>@Qualifier</code> or <code>@Primary</code>.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Factor beans in an ordered list", "One class per factor.", '<span class="pill ok">Chosen</span>'],
    ["One premium class", "Every change touches every price.", '<span class="pill bad">The starting point</span>'],
    ["<code>@Primary</code> to silence the error", "Starts, with only one factor.", '<span class="pill bad">The trap</span>'],
    ["List without <code>@Order</code>", "Order depends on scanning: unspecified.", '<span class="pill bad">The trap</span>'],
    ["Factors as configuration rows", "A rules format and its validation; no release per change.", '<span class="pill warn">When changes are frequent</span>']]) + """
<h2>Database design</h2>
<p>None in this station. If rates move to a database: a <code>premium_rates</code> table with effective dates (like station 016), and the quote records the rates it used, so a past quote can always be explained.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Fail fast</dt><dd>A wrong factor order is a wrong price for every customer. The startup check turns it into a deployment that never starts, which is far cheaper.</dd>
<dt>Scopes</dt><dd>Factors are singletons shared by all requests at once, so they hold no per-quote state. Anything per quote lives in local variables or the returned breakdown.</dd>
<dt>Explainability</dt><dd>The breakdown shows every step. Customers and regulators ask "why this price?"; the answer is in the response.</dd>
<dt>Money</dt><dd>Paise throughout, rounded per step and once more at the end, up, as the insurer's rule says.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What happens when you inject one bean and several exist?", "Spring fails with NoUniqueBeanDefinitionException. Fix it by injecting a List of all of them, or choosing one with @Qualifier; @Primary only sets a default."),
    ("In what order does Spring inject a List of beans?", "Sorted by @Order or the Ordered interface when present. Without them the order is not specified, so never rely on it."),
    ("@Qualifier or @Primary?", "@Primary marks the default for anyone who does not ask for a specific one. @Qualifier asks for a specific one. Use both: a sensible default, and explicit choices where it matters."),
    ("What is the default bean scope, and what follows?", "Singleton: one instance shared by every request. So beans must not keep per-request state in fields."),
    ("What is @PostConstruct for?", "Code that runs once after injection, before the bean is used: a good place to validate configuration and fail at startup."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can compute case 1's premium by hand."],
    ["Wiring", "A list in an explicit order.", "Why @Primary was the wrong fix."],
    ["Lifecycle", "The startup check.", "Other things worth checking at startup."],
    ["Explanation", "Why order changes the price.", "Factors in code versus factors in configuration."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist when several beans share a type:</p>
<ul class="rules">
<li>Does anything inject one where several exist, saved by a <code>@Primary</code>?</li>
<li>Does the order of a list matter, and is it written down with <code>@Order</code>?</li>
<li>Does any singleton keep per-request state in a field?</li>
<li>What happens at startup if the wiring is wrong?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
