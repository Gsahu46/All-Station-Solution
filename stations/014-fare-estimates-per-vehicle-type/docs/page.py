"""Station 014 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 14,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · strategy pattern · BigDecimal · MockMvc",
    "simulation": "Fares are estimates from demo rates, not any city's tariff. Road distance is the straight-line distance times 1.3, not a routing service. No ride is booked.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/rydo/fares/"
T = "src/test/java/com/rydo/fares/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Strategy pattern", "Put each way of doing a job in its own object, and let the caller pick one.", "Each counter in a bank has its own rules; you just go to the right counter.", "<code>FareRule</code>, held by each vehicle type."),
    ("Polymorphism", "Calling the same method on different objects, each answering its own way.", "Asking every shop \"what's the price?\"", "<code>rule.fare(km)</code>"),
    ("Open/closed principle", "Add new behaviour by adding code, not by editing code that already works.", "Adding a new counter without rebuilding the old ones.", "A new vehicle type is one new line."),
    ("BigDecimal", "Java's exact decimal number. <code>double</code> cannot hold 0.1 exactly.", "Counting coins instead of weighing them.", "Every fare calculation."),
    ("Rounding half up", "0.5 and above rounds up; below rounds down.", "₹57.50 is charged as ₹58.", "<code>RoundingMode.HALF_UP</code>"),
    ("Paise", "Whole hundredths of a rupee: no decimals in the answer.", "₹140 is 14000 paise.", "<code>farePaise</code>"),
]
STORY = [
    ("Rydo's fare code is one long if-else", "Bikes, autos and cabs are priced in a 300-line method with shared variables at the top."),
    ("Someone adds \"cab XL\"", "To make XL work, they change a shared default. Auto fares, which nobody touched, quietly rise from ₹150 to ₹190 for a 10 km ride."),
    ("The fix", "Each vehicle type owns its fare rule. The estimator asks every type the same question. Adding a type adds a line; it cannot change another type's fare."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">When rules for different things share one method and its variables, changing one thing changes the others. Give each thing its own rule.</p>

<h2>What are we building?</h2>
<p><code>GET /fare-estimates?pickup=lat,lng&amp;drop=lat,lng</code>: the server works out the road distance and returns a fare for every vehicle type. The client sends only the two points; it can never send a distance or a price.</p>

<h2>An everyday analogy</h2>
<p>A railway station has a separate fare chart for sleeper, 3A and 2A. When a new coach class is introduced, the railway prints a new chart; nobody edits the sleeper chart. One big chart with footnotes like "for 2A use the 3A rate plus…" is where mistakes creep in.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>Read the two points</strong> and check they are inside the service area.</li>
<li><strong>Work out the distance</strong> on the server, rounded to 0.1 km.</li>
<li><strong>Ask every vehicle type</strong> for its fare at that distance; each type's rule answers in its own way.</li>
<li><strong>Round to whole rupees</strong> (half up) and return paise.</li>
</ol>

<details class="qa check"><summary>Check yourself: why not let the app send the distance it already shows on the map?</summary><p>Because then anyone could send <code>distanceKm=1</code> for a 30 km ride and get a ₹30 fare. Anything that sets a price must be computed on the server from inputs the client cannot bend.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>Not real fares.</strong> Rates are demo rules.</li>
<li><strong>Not real road distance.</strong> Straight-line distance × 1.3; production asks a routing service.</li>
<li><strong>No surge, no booking.</strong> An estimate only.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Rydo</strong> (a fictional ride-hailing app in Bengaluru) prices bike, auto and cab rides in one long if-else. Adding "cab XL" changed a shared default and raised every auto fare; drivers noticed before the engineers did. The old app also sent the distance it computed, which a modified app could fake.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> MG Road to Koramangala, <b>then</b> the distance is 6.4 km and fares are bike ₹58, auto ₹96, cab ₹140, cab XL ₹208.</li>
<li><b>Given</b> the same point twice, <b>then</b> each vehicle's minimum: ₹30, ₹30, ₹80, ₹120.</li>
<li><b>Given</b> extra <code>distanceKm</code> or <code>fare</code> parameters, <b>then</b> they are ignored.</li>
<li><b>Given</b> a malformed or missing location, <b>then</b> <code>400</code>; outside the service area, <code>422</code>.</li>
<li><b>Given</b> a new vehicle type, <b>then</b> no existing fare changes.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Rates (demo rules): bike ₹20 + ₹6/km, min ₹30; auto ₹30 for the first 2 km + ₹15/km after; cab ₹50 + ₹14/km, min ₹80; cab XL ₹80 + ₹20/km, min ₹120.</li>
<li>Money is <code>BigDecimal</code> from strings; the answer is whole rupees (half up), returned in paise.</li>
<li>Distance is computed on the server, rounded to 0.1 km, and the fare uses that rounded number.</li>
<li>Service area: a demo rectangle around Bengaluru.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Replace an if-else chain with the strategy pattern: an interface and one rule per type.</li>
<li>Put behaviour on an enum, and explain the open/closed principle.</li>
<li>Calculate money with <code>BigDecimal</code> and an explicit rounding mode.</li>
<li>Explain why price inputs must never come from the client.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [["<code>GET</code>", "<code>/fare-estimates?pickup=lat,lng&amp;drop=lat,lng</code>", "Distance and a fare for every vehicle type."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "Both points valid and in the service area"],
    ['<span class="pill warn">400</span>', "A point is missing, not <code>lat,lng</code>, or out of range"],
    ['<span class="pill warn">422</span>', "A point is outside the service area"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-mg-road-to-koramangala", "Case 1: MG Road to Koramangala", "<b>Why:</b> 6.4 km by the server's estimate. Each vehicle's rule gives its own fare: the cab's ₹139.60 rounds half up to ₹140."),
    ("02-client-sends-a-distance", "Case 2: a client tries to set the distance", "<b>Why:</b> <code>distanceKm=1</code> and <code>fare=10</code> are not parameters of this endpoint; the answer is the same as case 1."),
    ("03-same-point", "Case 3: pickup equals drop", "<b>Why:</b> 0 km, so each vehicle's minimum fare."),
    ("04-not-a-location", "Case 4: a place name instead of coordinates", "<b>Why:</b> <code>400</code>; the app must send coordinates."),
    ("05-outside-area", "Case 5: a drop in Mumbai", "<b>Why:</b> a valid point, but outside the service area: <code>422</code>."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["MG Road → Koramangala", "6.4 km; ₹58, ₹96, ₹140, ₹208", "<code>everyVehicleTypeGetsAnEstimateFromTheServersDistance</code>"],
    ["Same point", "Each minimum", "<code>aVeryShortRidePaysEachMinimum</code>"],
    ["Client sends distance or fare", "Ignored", "<code>distanceOrFareSentByTheClientIsIgnored</code>"],
    ["Auto at 0, 2.0, 2.1, 3.0 km", "₹30, ₹30, ₹32, ₹45", "<code>theAutoMeterIncludesTheFirstTwoKm</code>"],
    ["Short bike and cab rides", "Minimums, then per-km", "<code>minimumsApplyToShortRides</code>"],
    ["₹57.50, ₹139.60", "₹58, ₹140", "<code>halfARupeeRoundsUp</code>"],
    ["0.1 + 0.2", "<code>double</code> is off; <code>BigDecimal</code> is exact", "<code>doubleArithmeticIsNotExactForMoney</code>"],
    ["Place name, latitude 95, missing drop", "<code>400</code>", "<code>aMalformedOrMissingLocationIs400</code>"],
    ["Mumbai", "<code>422</code>", "<code>aPointOutsideTheServiceAreaIs422</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">A growing if-else chain where adding one vehicle type breaks another.</p>
<p>The "before" method starts with the auto's numbers as defaults and overrides them per branch. Cab XL was added by raising a default, since XL "uses the defaults". The first test shows the result: a 10 km auto ride now costs ₹190 instead of ₹150. The second test asks the real rules: each type has its own, so XL's numbers cannot reach the auto. Removing the "never below zero" guard from the auto meter was tried while building: 2 tests went red.</p>
</div>
""" + code(read(T + "IfElseChainTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "FareEstimateController.java", dwn("Reads the two points, computes the distance, asks every vehicle type for a fare.",
        "No vehicle is special-cased: the loop asks each one the same question.",
        "No API; and with a distance parameter, a client could set its own price.")),
    (J + "Location.java", dwn("Parses <code>lat,lng</code>, checks the service area, and estimates road distance.", "One place for geography.", "Coordinates parsed in several places.",
        "<ul><li>Haversine gives the straight-line distance on a sphere; × 1.3 is a demo allowance for roads.</li></ul>")),
    (J + "VehicleType.java", dwn("An enum where each value holds its fare rule; rounds to whole rupees and returns paise.",
        "The type and its rule live together: a new type is one line.",
        "The if-else chain, and its shared variables.",
        "<ul><li>Amounts are built from strings: <code>new BigDecimal(\"0.1\")</code> is exact, <code>new BigDecimal(0.1)</code> is not.</li><li><code>longValueExact</code> fails loudly instead of silently cutting digits.</li></ul>")),
    (J + "FareRule.java", dwn("The strategy interface: distance in, rupees out.", "The estimator depends only on this.", "Every caller would need to know every rule.")),
    (J + "PerKmRule.java", "<p>Base + per km, with a minimum. Used by bikes and cabs.</p>"),
    (J + "MeterRule.java", "<p>Auto meter: the first km are included in the base.</p>"),
    ("src/main/resources/application.yaml", "<p>RFC 9457 problem bodies for every error.</p>"),
    (J + "FaresApplication.java", "<p>Standard Spring Boot entry point.</p>"),
]
tree = """stations/014-fare-estimates-per-vehicle-type/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/rydo/fares/
│   ├── FareEstimateController.java   ├── Location.java    ├── VehicleType.java
│   ├── FareRule.java                 ├── PerKmRule.java   ├── MeterRule.java
│   └── FaresApplication.java
├── src/test/java/com/rydo/fares/   (see Tests)
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
""" + code("""# MG Road to Koramangala: expect "distanceKm": 6.4
curl "http://localhost:8080/fare-estimates?pickup=12.9756,77.6066&drop=12.9352,77.6245"

# Try to set your own distance: nothing changes
curl "http://localhost:8080/fare-estimates?pickup=12.9756,77.6066&drop=12.9352,77.6245&distanceKm=1\"""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["Only <code>pickup</code> arrives", "The shell cut the URL at <code>&amp;</code>.", "Put the URL in double quotes."],
    ["<code>422 Outside service area</code>", "The demo area is a rectangle around Bengaluru.", "Use points between latitude 12.80–13.25 and longitude 77.40–77.80."],
    ["<code>release version 25 not supported</code>", "Maven is using an older JDK.", "Point <code>JAVA_HOME</code> at JDK 25, or add <code>-Djava.version=21</code>."]]) + """
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>FareEstimateContractTest</code> ({cnt('FareEstimateContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>IfElseChainTrapTest</code> ({cnt('IfElseChainTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "Each rule at its boundaries; rounding", f"<code>FareRulesTest</code> ({cnt('FareRulesTest')})", '<span class="pill ok">pass</span>']]) + """
<p class="note">The contract tests look each vehicle up by name instead of checking the exact list. A test that lists every vehicle type would itself break whenever a type is added: the same closed-to-extension mistake as the if-else chain.</p>
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "IfElseChainTrapTest.java", "<p>Written first: the shared default that moved the auto fare; <code>double</code> against <code>BigDecimal</code>.</p>"),
    (T + "FareEstimateContractTest.java", "<p>Real coordinates, minimums, ignored price inputs, refusals.</p>"),
    (T + "FareRulesTest.java", "<p>Each rule at its boundaries; half-up rounding; the distance.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the whole app through MockMvc.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/rydo/fares/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=EvCabChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Launch EV cabs", "Beginner-friendly", 15,
    "Add <code>EV_CAB</code>: ₹50 base, ₹12 per km, ₹80 minimum. Every other fare must stay exactly the same.",
    "<code>EvCabChallengeTest</code> passes, and the station's tests still pass.",
    ["One new enum value with a <code>PerKmRule</code>. If you find yourself editing anything else, stop and ask why."],
    "challenge/EvCabChallengeTest.java", ["challenge/solution/VehicleType.java"]) + challenge(2, "Airport toll", "Go deeper", 30,
    "Trips that end at the airport (a demo box: latitude 13.18–13.22, longitude 77.68–77.73) add a ₹120 toll for cars; bikes and autos do not pay it.",
    "both tests in <code>AirportTollChallengeTest</code> pass.",
    ["Whether a vehicle pays tolls is a fact about the vehicle type: put it on the enum.",
     "Whether a trip ends at the airport is a fact about the location: put it on <code>Location</code>.",
     "Add the toll in paise after rounding the fare, so it is never rounded."],
    "challenge/AirportTollChallengeTest.java", ["challenge/solution/VehicleType.java", "challenge/solution/Location.java", "challenge/solution/FareEstimateController.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Night fares and surge</h2>
<p>Autos charge 1.5× between 11 p.m. and 5 a.m., and cabs may have a demand multiplier. Sketch both as rules that wrap another rule (a decorator). In which order do you apply night fare, surge and the minimum? Where does "now" come from, and how do you test 10:59 p.m. and 11:00 p.m.?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the shared default moves the auto fare.</li>
<li>Write the <code>FareRule</code> interface and the two rule shapes (per km, meter).</li>
<li>Give each vehicle type its rule on the enum.</li>
<li>Compute distance on the server; round fares with an explicit mode; return paise.</li>
<li>Test each rule at its boundaries, independently of HTTP.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Strategy objects held by an enum", "A small interface and one record per rule shape.", '<span class="pill ok">Chosen</span>'],
    ["One method with if-else or switch on a string", "Shared variables; every change touches every type (the trap).", '<span class="pill bad">Wrong</span>'],
    ["A subclass per vehicle type", "Works for this, but inheritance is heavier than needed (station 012).", '<span class="pill warn">Possible</span>'],
    ["Rates in configuration or a database", "Change prices without a release; needs validation and an audit trail.", '<span class="pill warn">In production</span>'],
    ["<code>double</code> for money", "0.1 + 0.2 ≠ 0.3; rounding errors add up across millions of rides.", '<span class="pill bad">Wrong</span>']]) + """
<h2>Database design</h2>
<p>None. In production, rates would be dated rows (vehicle type, base, per km, minimum, valid from), so a change takes effect at a set time and old receipts can still be explained.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Security</dt><dd>Prices come only from server-side inputs: coordinates are validated, the area is checked, the distance is the server's. The final fare at the end of a real ride would be computed again from the trip's own data.</dd>
<dt>Money</dt><dd>Exact decimals, one explicit rounding step, whole rupees in paise. Show riders the distance the fare was computed from.</dd>
<dt>Maintainability</dt><dd>A new vehicle type is one line; tests look types up by name, so they do not break either.</dd>
<dt>Accuracy</dt><dd>Straight-line × 1.3 is a demo; real estimates use routing and traffic, and are labelled "estimate".</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is the strategy pattern?", "Each way of doing a job is its own object behind a shared interface; the caller holds one and calls it without knowing which. New behaviour means a new strategy, not edits to existing ones."),
    ("What is the open/closed principle?", "Code should be open for extension and closed for modification: add a vehicle type by adding code, without changing code that already works and is tested."),
    ("Why not double for money?", "double is binary floating point and cannot represent most decimal fractions exactly (0.1 + 0.2 = 0.30000000000000004). Use BigDecimal (built from strings) or whole minor units."),
    ("How do you round money in Java?", "setScale with an explicit RoundingMode, once, at a documented step. Never let a library pick a default."),
    ("Why compute the distance on the server?", "Anything that sets a price must not come from the client, which can be modified. The client sends facts (coordinates); the server derives the price."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can work out the fare for any distance by hand."],
    ["Design", "One rule per vehicle type.", "You can add night fares as a decorator on paper."],
    ["Money", "BigDecimal and one rounding step.", "You can explain why the fare uses the rounded distance."],
    ["Explanation", "Strategy and open/closed in one sentence each.", "You can name the shared-variable bug in someone else's if-else."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on pricing code:</p>
<ul class="rules">
<li>Does adding a type mean editing a shared method?</li>
<li>Is any money a <code>double</code>, or a <code>BigDecimal</code> built from a <code>double</code>?</li>
<li>Is rounding explicit, and done once?</li>
<li>Can any input that affects the price come from the client?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
