"""Station 030 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 30,
    "stack": "Spring Boot 4.1.1 · Java 25 · @ConfigurationProperties records · @Validated · profiles · relaxed binding · @AutoConfiguration · MockMvc",
    "simulation": "Delivery terms are demo values, not Basketo's. A delivery check only answers whether an order could be delivered; no order is placed. Distances are straight-line, computed on the server.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/basketo/delivery/"
T = "src/test/java/com/basketo/delivery/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Configuration", "Values the app reads at startup instead of having them in code.", "A shop's price list on the wall.", "<code>application.yaml</code>"),
    ("Configuration properties", "A Java record that Spring fills from configuration.", "A form filled from the price list.", "<code>DeliverySettings</code>"),
    ("Fail fast", "Refuse to start when something is wrong, instead of running wrong.", "A pilot's checklist before take-off.", "<code>@Validated</code>"),
    ("Profile", "A named set of extra configuration for one environment.", "A weekend menu on top of the usual one.", "<code>application-dev.yaml</code>"),
    ("Environment variable override", "A value set outside the app that replaces one in the file.", "A sticky note over one price.", "<code>BASKETO_CITIES_PUNE_FEEPAISE</code>"),
    ("Auto-configuration", "A default bean Spring Boot adds only if you have not added your own.", "A spare key, used only if you did not bring yours.", "<code>DistanceAutoConfiguration</code>"),
]
STORY = [
    ("A config change goes out", "Someone edits Pune's settings and types <code>minimun-order-paise</code>. The app starts, as always."),
    ("Nothing fails, and that is the problem", "The real key is now missing, so the minimum order is 0. Customers in Pune order a single ₹10 lemon with free-feeling delivery, and every order loses money. Meanwhile the app also trusts the distance the phone sends."),
    ("The fix", "Bind settings into a validated record that refuses unknown keys, missing values and impossible numbers at startup, and compute distance on the server from the address."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A bad setting should stop the deployment, not reach a customer.</p>

<h2>What are we building?</h2>
<p><code>GET /cities/{city}/delivery-terms</code> shows a city's radius, fee and minimum order. <code>POST /delivery-checks</code> says whether an address and an order amount can be delivered, with the distance the server computed.</p>

<h2>An everyday analogy</h2>
<p>A restaurant's opening checklist: if the gas reading is missing or impossible, the kitchen does not open. It does not open and hope the reading was fine.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>At startup</strong>, Spring binds <code>basketo.cities.*</code> into records, with profile and environment overrides applied.</li>
<li><strong>It validates them</strong>: unknown keys, missing values, a radius over 15 km or a minimum under ₹99 stop the start, naming the property.</li>
<li><strong>A check arrives</strong> with coordinates; the server computes the distance from the city's store.</li>
<li><strong>It answers</strong> with the distance, the fee, and any reasons it cannot deliver.</li>
</ol>

<details class="qa check"><summary>Check yourself: why use <code>Long</code> instead of <code>long</code> for the minimum order?</summary><p>A missing <code>long</code> silently becomes 0. A missing <code>Long</code> is <code>null</code>, which <code>@NotNull</code> refuses, so a misspelt key is caught at startup.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No road distances.</strong> Straight-line distance; a road service could replace it.</li>
<li><strong>No live config changes.</strong> Settings are read at startup; challenge 3 discusses changes without a restart.</li>
<li><strong>No orders.</strong> A check only.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Basketo</strong> (a fictional quick-commerce app) sets a delivery radius, fee and minimum order per city. A typo in a config key once set a minimum order to ₹0 and nothing failed. The delivery check also used the distance the app sent, so a modified client could get delivery anywhere.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> a misspelt key, a missing value, a minimum below ₹99 or a radius over 15 km, <b>then</b> the app does not start, and the error names the property.</li>
<li><b>Given</b> an extra key nobody reads, <b>then</b> the app does not start.</li>
<li><b>Given</b> <code>BASKETO_CITIES_PUNE_FEEPAISE=3000</code>, <b>then</b> Pune's fee is ₹30 and its other values come from the file.</li>
<li><b>Given</b> the <code>dev</code> profile, <b>then</b> a test city exists; without it, it does not.</li>
<li><b>Given</b> an address in Koregaon Park, <b>then</b> 4.94 km from the Pune store, deliverable; Hinjewadi at 13.28 km with ₹99 is not, for two reasons.</li>
<li><b>Given</b> a <code>distanceKm</code> in the request, <b>then</b> <code>400</code>; an unknown city, <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Demo limits: radius 0.5 to 15 km; fee ₹0 to ₹100; minimum order at least ₹99.</li>
<li>Settings are records with wrapper types and validation; unknown keys are an error.</li>
<li>Distance is computed on the server (haversine, mean Earth radius 6,371.0088 km).</li>
<li>City names are normalised with <code>Locale.ROOT</code>.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Bind configuration into records with <code>@ConfigurationProperties</code>.</li>
<li>Make configuration fail fast with <code>@Validated</code> and <code>ignoreUnknownFields = false</code>.</li>
<li>Use profiles and environment variable overrides.</li>
<li>Explain auto-configuration and <code>@ConditionalOnMissingBean</code>.</li>
<li>Compute on the server what the client could lie about.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/cities/{city}/delivery-terms</code>", "Radius, fee and minimum order for a city."],
    ["<code>POST</code>", "<code>/delivery-checks</code>", "<code>{\"city\", \"lat\", \"lon\", \"orderPaise\"}</code>: can this be delivered, and why not?"]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "Terms; a check (deliverable or not, with reasons)"],
    ['<span class="pill warn">400</span>', "Coordinates out of range, a missing field, a fraction of a paisa, or a <code>distanceKm</code>"],
    ['<span class="pill warn">404</span>', "A city Basketo does not serve"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-pune-terms", "Case 1: Pune's terms", "<b>Why:</b> straight from the validated settings."),
    ("02-an-address-in-range", "Case 2: Koregaon Park, ₹250", "<b>Why:</b> 4.94 km from the store, inside 6 km, above ₹149: deliverable."),
    ("03-too-far-and-too-small", "Case 3: Hinjewadi, ₹99", "<b>Why:</b> 13.28 km and below the minimum: both reasons, so the app can say both."),
    ("04-the-client-sends-its-own-distance", "Case 4: the app sends \"distanceKm\": 0", "<b>Why:</b> not a field any more: <code>400</code>, so a client cannot keep believing its own number is used."),
    ("05-a-city-we-do-not-serve", "Case 5: Jaipur", "<b>Why:</b> <code>404</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Minimum 0; radius 60; minimum missing", "The app does not start", "<code>invalidValuesStopTheAppStartingAndNameTheProperty</code>"],
    ["An extra misspelt key", "The app does not start", "<code>aMisspeltExtraKeyStopsTheAppStartingToo</code>"],
    ["An environment variable for one value", "That value replaced, the rest from the file", "<code>anEnvironmentVariableOverridesOneValue</code>"],
    ["The dev profile", "A test city appears", "<code>theDevProfileAddsATestCity</code>"],
    ["Your own <code>DistanceCalculator</code> bean", "The default steps aside", "<code>aBeanOfYourOwnReplacesTheDefaultCalculator</code>"],
    ["Pune to Mumbai", "120.15 km straight-line", "<code>straightLineDistanceMatchesAKnownOne</code>"],
    ["Terms; in range; out of range and too small", "As specified", "<code>DeliveryContractTest</code>"],
    ["A client-sent distance", "<code>400</code>", "<code>theServerSaysTooFarAndTooSmallWhateverTheClientThinks</code>"],
    ["Jaipur", "<code>404</code>", "<code>aCityWeDoNotServeIs404</code>"],
    ["Latitude 91; zero or fractional amounts; a missing field", "<code>400</code>", "<code>badCoordinatesOrAmountsAre400</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Unvalidated config: a typo sets the minimum order to zero and nothing fails.</p>
<p>The first test binds the old settings (primitives, no validation) with the typo: the app starts and Pune's minimum is 0. The second binds the real settings with the same typo: the start fails, naming <code>cities[pune].minimumOrderPaise</code> as null. The third shows the old check believing a client's 0 km. While building, removing <code>@Validated</code> turned 2 tests red, and allowing unknown keys turned 1 red.</p>
</div>
""" + code(read(T + "UnvalidatedConfigTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "DeliveryController.java", dwn("Finds the city's settings and runs the check with the server's own distance.",
        "No distance in the request at all: there is nothing for a client to lie about.",
        "Trusting a <code>distanceKm</code> from the app.")),
    (J + "DeliverySettings.java", dwn("The settings as validated records.",
        "Wrapper types, constraints and <code>ignoreUnknownFields = false</code>: every bad setting stops the start.",
        "The trap: primitives that default to 0, and no checks.",
        "<ul><li><code>@Validated</code> runs Bean Validation on the bound record at startup.</li><li><code>@Valid</code> on the map values and the store location checks the nested records too.</li></ul>")),
    (J + "DistanceAutoConfiguration.java", dwn("The default distance calculator, as an auto-configuration.",
        "Listed in <code>META-INF/spring/…AutoConfiguration.imports</code>, so it runs after the app's own beans and <code>@ConditionalOnMissingBean</code> can see them.",
        "The same condition on an ordinary <code>@Configuration</code>: its result depends on the order definitions are processed. Spring Boot's documentation recommends the condition only on auto-configuration classes.")),
    (J + "DistanceCalculator.java", "<p>The one-method interface any distance source implements.</p>"),
    ("src/main/resources/application.yaml", "<p>The demo cities, strict JSON, and a note on environment overrides.</p>"),
    ("src/main/resources/application-dev.yaml", "<p>The <code>dev</code> profile: a test city for testers.</p>"),
    ("src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports", "<p>Registers the auto-configuration.</p>"),
    (J + "DeliveryApplication.java", "<p>Entry point; <code>@ConfigurationPropertiesScan</code> finds the settings record.</p>"),
]
tree = """stations/030-per-city-delivery-settings/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/basketo/delivery/
│   ├── DeliveryController.java   ├── DeliverySettings.java
│   ├── DistanceCalculator.java   ├── DistanceAutoConfiguration.java   └── DeliveryApplication.java
├── src/main/resources/
│   ├── application.yaml   ├── application-dev.yaml
│   └── META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports
├── src/test/java/com/basketo/delivery/   (see Tests)
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
""" + code("""./mvnw spring-boot:run                                         # the API on http://localhost:8080
./mvnw spring-boot:run -Dspring-boot.run.profiles=dev          # with the dev profile's test city
BASKETO_CITIES_PUNE_FEEPAISE=3000 ./mvnw spring-boot:run       # one value overridden
./mvnw test                                                    # all """ + str(N_TESTS) + """ tests""", "bash") + """
<p><strong>Windows (PowerShell)</strong></p>
""" + code(""".\\mvnw.cmd spring-boot:run
$env:BASKETO_CITIES_PUNE_FEEPAISE = "3000"; .\\mvnw.cmd spring-boot:run
.\\mvnw.cmd test""", "powershell") + """
<p class="muted">On JDK 21, add <code>-Djava.version=21</code>. Nothing here needs a Java 25 feature.</p>
<h2>Try it yourself</h2>
<p>Break the configuration on purpose: change <code>minimum-order-paise</code> to <code>minimun-order-paise</code> in <code>application.yaml</code> and start the app. It refuses, naming the property. Put it back.</p>
""" + code("""curl -X POST http://localhost:8080/delivery-checks -H "Content-Type: application/json" \\
     -d '{"city":"pune","lat":18.5362,"lon":73.8940,"orderPaise":25000}'""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>Binding validation errors on basketo</code> at startup", "A value is missing or out of range.", "Read the field it names, and fix that line."],
    ["<code>Could not bind properties to 'DeliverySettings'</code>", "An unknown key, often a typo.", "Check the spelling of each key under <code>basketo.cities</code>."],
    ["An environment variable has no effect", "The name does not map to the key.", "Upper case, dots and dashes removed: <code>basketo.cities.pune.fee-paise</code> is <code>BASKETO_CITIES_PUNE_FEEPAISE</code>."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels, then the configuration behind it.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "The trap test was written first.") + """
<h2>Required tests for this station</h2>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>DeliveryContractTest</code> ({cnt('DeliveryContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>UnvalidatedConfigTrapTest</code> ({cnt('UnvalidatedConfigTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "Validation, environment, profiles, auto-configuration, distance", f"<code>DeliveryConfigTest</code> ({cnt('DeliveryConfigTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "UnvalidatedConfigTrapTest.java", "<p>Written first: the old settings start with a typo; the real ones refuse.</p>"),
    (T + "DeliveryConfigTest.java", "<p>Startup failures, an environment variable, the dev profile, a replaced default, and a known distance.</p>"),
    (T + "DeliveryContractTest.java", "<p>Terms and checks through HTTP, and every refusal.</p>"),
    (T + "ConfigRunner.java", "<p>A tiny context with only the settings, binding and validation: fails or starts in milliseconds.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/basketo/delivery/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=FreeDeliveryChallengeTest</code> (the app refuses the new key until you add it).</li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Free delivery above a threshold", "Beginner-friendly", 25,
    "Add an optional <code>free-delivery-above-paise</code> per city. Orders at or above it pay no fee. It must be above the city's minimum order, or the app does not start.",
    "both tests in <code>FreeDeliveryChallengeTest</code> pass.",
    ["An optional <code>Long</code>: <code>null</code> means no threshold.",
     "A rule across two fields: an <code>@AssertTrue</code> method named <code>isSomething()</code> on the record."],
    "challenge/FreeDeliveryChallengeTest.java", ["challenge/solution/DeliverySettings.java", "challenge/solution/DeliveryController.java"]) + challenge(2, "Fees by distance band", "Go deeper", 35,
    "Add optional <code>fee-bands</code> per city (up to 3 km ₹15, up to 6 km ₹30, …) that replace the flat fee. Bands must increase and the last must reach the radius, or the app does not start.",
    "both tests in <code>DistanceBandsChallengeTest</code> pass, and the station's tests still pass.",
    ["A list of records binds from <code>fee-bands[0].up-to-km</code> and so on.",
     "The fee uses the server's distance: the first band whose limit is not below it."],
    "challenge/DistanceBandsChallengeTest.java", ["challenge/solution/DeliverySettings.java", "challenge/solution/DeliveryController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Changing settings without a restart</h2>
<p>Operations wants to raise Mumbai's fee during heavy rain, in minutes. Compare a restart with new environment variables, a settings table in the database, and a config server. How does each one keep the fail-fast checks of this station, and what does a customer see while the change rolls out?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the old settings start with a typo and a zero minimum.</li>
<li>Write the settings as records with wrapper types and constraints; refuse unknown keys.</li>
<li>Test startup failures in small contexts; test profiles and environment overrides on the real app.</li>
<li>Move the distance into the server, behind a replaceable default.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Validated <code>@ConfigurationProperties</code> records", "A record and its constraints.", '<span class="pill ok">Chosen</span>'],
    ["<code>@Value</code> on each field", "No validation in one place; typos become defaults or startup errors one by one.", '<span class="pill warn">For one or two values</span>'],
    ["Primitives and no validation", "A missing value becomes 0.", '<span class="pill bad">The trap</span>'],
    ["Ignoring unknown keys", "A misspelt extra key is silently ignored.", '<span class="pill bad">Hides typos</span>'],
    ["The client's distance", "Any client can claim 0 km.", '<span class="pill bad">Never</span>']]) + """
<h2>Database design</h2>
<p>None in this station. If settings move to a table: <code>city_delivery_terms</code> with check constraints mirroring the record's (radius between 0.5 and 15, minimum at least 9900), so a bad row is refused by the database too.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Deployments</dt><dd>A bad setting now fails the deployment's startup, so the old version keeps serving. That is the point: the error reaches an engineer, not a customer.</dd>
<dt>Secrets and environments</dt><dd>Per-environment values come from environment variables or a secret store, never committed. Profiles hold whole sets of differences (dev, staging).</dd>
<dt>Trust</dt><dd>Anything the client could change (distance, price, discount) is computed or looked up on the server.</dd>
<dt>Distance</dt><dd>Straight-line distance is always shorter than the road. A real radius check may use a routing service, plugged in as its own <code>DistanceCalculator</code>.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("How do you make Spring Boot configuration fail fast?", "Bind it into a @ConfigurationProperties class or record, add @Validated with Bean Validation constraints, use wrapper types so missing values are null, and set ignoreUnknownFields = false so typos are errors."),
    ("How does an environment variable override a property?", "Relaxed binding: upper case, dots to underscores, dashes removed. basketo.cities.pune.fee-paise becomes BASKETO_CITIES_PUNE_FEEPAISE, and it wins over application.yaml."),
    ("What is a profile?", "A named set of configuration (application-dev.yaml) applied on top of the defaults when the profile is active."),
    ("What is auto-configuration?", "Configuration classes Spring Boot applies after your own beans, usually with conditions like @ConditionalOnMissingBean, so they supply sensible defaults you can replace by defining your own bean."),
    ("Why compute the distance on the server?", "The client controls everything it sends. A value that decides price or eligibility must come from data the server trusts."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You broke the config on purpose and read the error."],
    ["Configuration", "Validated records, no unknown keys.", "You can map any property to its environment variable."],
    ["Spring Boot", "Profiles and overrides.", "Why <code>@ConditionalOnMissingBean</code> belongs on auto-configuration."],
    ["Explanation", "Why <code>Long</code>, not <code>long</code>.", "What the server must never take from the client."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any configuration change:</p>
<ul class="rules">
<li>Does a typo in a key stop the app, or quietly change a value?</li>
<li>Which values have limits, and are they checked at startup?</li>
<li>Are environment-specific values outside the repository?</li>
<li>Does any setting depend on something the client sends?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
