"""Station 012 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 12,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · interfaces, enums, records · MockMvc",
    "simulation": "Five vehicles are fixed in the code. Service intervals are demo rules, not any manufacturer's schedule.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/dakroute/fleet/"
T = "src/test/java/com/dakroute/fleet/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Inheritance", "A class takes everything from a parent class (<code>extends</code>).", "A child inheriting the family house, leaks and all.", "The trap's <code>OldEvVan extends OldVan</code>."),
    ("Abstract class", "A parent class that cannot be created on its own and can hold shared code and fields.", "A recipe base: \"every curry starts with onions\".", "The trap's <code>OldVehicle</code>."),
    ("Interface", "A promise of what a class can do, with no stored data.", "A plug socket shape: anything that fits can be plugged in.", "<code>ServiceItems</code>: \"I can list service tasks\"."),
    ("Composition", "Building something out of parts it has, instead of a parent it is.", "A thali: you choose the dishes, nothing comes with the plate.", "A vehicle has a powertrain and a body."),
    ("Polymorphism", "Calling the same method on different kinds of objects, each answering its own way.", "Asking every guest \"what will you eat?\"", "<code>part.tasks()</code> on a powertrain or a body."),
    ("Fragile base class", "A change in a parent class breaks children that never asked for it.", "Changing the house's wiring, and every flat's lights flicker.", "A diesel filter task added for trucks appears on bikes."),
]
STORY = [
    ("Dakroute's fleet app grew one class at a time", "Vehicle, then FuelVehicle, then Truck, Van and Bike underneath, with shared code copied between them."),
    ("An EV van arrived", "It was made a subclass of Van, so it inherited an engine oil change. Fixing that took changes in nine places, and someone's \"diesel filter for trucks\" in the shared parent showed up on petrol bikes."),
    ("The fix", "Describe a vehicle by its parts: a powertrain (diesel, petrol, electric) and a body (truck, van, two-wheeler). Each part lists its own tasks; a vehicle's plan is its parts' tasks together."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">"Is a" is a strong promise: a child gets everything the parent has, today and after every future change. "Has a" lets you pick exactly the parts you need.</p>

<h2>What are we building?</h2>
<p><code>GET /fleet/vehicles/{id}/service-plan</code>: the maintenance tasks for one vehicle, each with the kilometre reading when it is next due, soonest first. An EV van gets battery checks and van checks, and never an oil change.</p>

<h2>An everyday analogy</h2>
<p>A tiffin service. One way is to have a "North Indian Thali", a "North Indian Thali Without Onion", a "Jain North Indian Thali Without Onion", each a copy of the one above with changes. The other way is to let each customer choose a base, a dal and a sabzi. The second way never serves onions to a Jain customer by accident when the base thali changes.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>A vehicle is two parts</strong>: a powertrain and a body.</li>
<li><strong>Each part lists its tasks</strong>, such as "Engine oil change every 15,000 km" for diesel or "Brake check every 15,000 km" for a van.</li>
<li><strong>The planner asks each part</strong> for its tasks without knowing which part it is (polymorphism).</li>
<li><strong>For each task</strong>, the next due reading is the next multiple of its interval; the list is sorted soonest first.</li>
</ol>

<details class="qa check"><summary>Check yourself: Dakroute buys a CNG van. With composition, what has to change?</summary><p>Only a new powertrain value, CNG, with its own tasks, and the van itself in the fleet list. The body VAN, the planner and every other vehicle stay untouched. Practice challenge 1 does exactly this.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No service history.</strong> "Next due" is the next multiple of the interval, not based on when the work was last done.</li>
<li><strong>Not real schedules.</strong> Intervals are demo rules; real ones come from each manufacturer's manual.</li>
<li><strong>No database.</strong> Five vehicles are fixed in code.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Dakroute</strong> (a fictional logistics company) runs trucks, vans and two-wheelers. Its fleet app models them as a tree of classes. When the first EV van arrived, it was added as a subclass of Van and inherited an engine oil change, so the workshop booked oil changes for an electric van. Removing it touched nine classes. A month later a "diesel particulate filter" task, added to the shared fuel-vehicle parent for trucks, appeared on every petrol bike.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> a diesel truck at 128,400 km, <b>then</b> its plan has the diesel tasks and the truck tasks, soonest first; the 15,000 km oil change is next due at 135,000 km (in 6,600 km).</li>
<li><b>Given</b> an electric van, <b>then</b> its plan has battery and van tasks and no engine oil change.</li>
<li><b>Given</b> a petrol two-wheeler, <b>then</b> no diesel tasks, and the petrol oil interval (10,000 km).</li>
<li><b>Given</b> a task within 10% of its interval, <b>then</b> it is marked <code>dueSoon</code>.</li>
<li><b>Given</b> an unknown vehicle, <b>then</b> <code>404</code>; a non-numeric id, <code>400</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>A vehicle is a powertrain plus a body. Each contributes its own tasks; nothing is inherited.</li>
<li>Next due = the next multiple of the interval at or above the odometer (at least one interval).</li>
<li>Tasks are sorted by km until due, then by name.</li>
<li>Errors are RFC 9457 problems.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Explain the difference between an abstract class and an interface, and when each fits.</li>
<li>Prefer composition to inheritance, and say why.</li>
<li>Use polymorphism through an interface implemented by enums.</li>
<li>Recognise the fragile base class problem in code you review.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoint</h2>
""" + table(["Method", "Path", "Purpose"], [["<code>GET</code>", "<code>/fleet/vehicles/{id}/service-plan</code>", "The vehicle's parts and its tasks, soonest first."]]) + """
<h2>Each task</h2>
""" + table(["Field", "Meaning"], [
    ["<code>task</code>, <code>everyKm</code>", "What to do, and how often."],
    ["<code>nextDueKm</code>, <code>dueInKm</code>", "The odometer reading when it is next due, and how far away that is."],
    ["<code>dueSoon</code>", "Within 10% of the interval (a demo rule)."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">200</span>', "The vehicle exists"],
    ['<span class="pill warn">400</span>', "The id is not a number"],
    ['<span class="pill warn">404</span>', "No such vehicle"]]) + """
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-diesel-truck", "Case 1: the diesel truck", "<b>Why:</b> DIESEL tasks plus TRUCK tasks, soonest first. Two tasks due in 1,600 km are ordered by name."),
    ("02-ev-van", "Case 2: the EV van", "<b>Why:</b> ELECTRIC plus VAN: battery checks and van checks, no oil change. The battery check is <code>dueSoon</code> (1,050 km of a 20,000 km interval)."),
    ("03-petrol-bike", "Case 3: the petrol two-wheeler", "<b>Why:</b> PETROL plus TWO_WHEELER: a 10,000 km oil change, chain lubrication, no diesel filter."),
    ("04-unknown", "Case 4: unknown vehicle", "<b>Why:</b> <code>404</code> problem."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Diesel truck", "Diesel and truck tasks, soonest first, ties by name", "<code>aDieselTruckGetsEngineAndTruckTasksSoonestFirst</code>"],
    ["Electric van", "Battery and van tasks; dueSoon at 10%", "<code>anElectricVanGetsBatteryAndVanTasks</code>"],
    ["Petrol two-wheeler", "Petrol interval; no diesel tasks", "<code>aPetrolBikeGetsEngineAndTwoWheelerTasks</code>, <code>composedVehiclesGetOnlyTheTasksOfTheirOwnParts</code>"],
    ["Every one of the 9 combinations", "Exactly its two parts' tasks", "<code>everyCombinationOfPartsGetsExactlyTheTasksOfItsTwoParts</code>"],
    ["Odometer 0, 14,999, exactly 30,000, 30,001", "Due at 15,000; 15,000; now; 45,000", "<code>nextDueIsTheNextMultipleOfTheInterval</code>"],
    ["Unknown vehicle; id \"truck\"", "<code>404</code>; <code>400</code>", "<code>anUnknownVehicleIs404AndANonNumberIs400</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Deep inheritance trees where one change in the base class breaks every vehicle.</p>
<p>The "before" code is a tree of abstract classes: <code>OldVehicle</code> → <code>OldFuelVehicle</code> → <code>OldVan</code> → <code>OldEvVan</code>. Each step looks reasonable. The first test shows the result: the EV van inherits an oil change, and a task added to the fuel parent "for the trucks" lands on a petrol bike. The second test asks the real API, built from parts, and neither happens. Removing the body from <code>Vehicle.parts()</code> was tried while building: 4 tests went red.</p>
</div>
""" + code(read(T + "DeepInheritanceTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "ServicePlanController.java", dwn("Finds the vehicle and returns its plan.", "HTTP in one place.", "No API.")),
    (J + "Vehicle.java", dwn("A record that <em>has</em> a powertrain and a body.",
        "Composition: any powertrain goes with any body, with no new class.",
        "A class per combination (EvVan, DieselVan, PetrolVan…), each inheriting from something.")),
    (J + "ServiceItems.java", dwn("The interface: \"I can list service tasks\".",
        "It is all the planner needs to know about a part.",
        "The planner would need an <code>if</code> for every kind of part.")),
    (J + "Powertrain.java", dwn("An enum that implements <code>ServiceItems</code>: each value carries its tasks.", "Adding CNG is one new value.", "Tasks spread over subclasses.")),
    (J + "Body.java", dwn("The same idea for bodies.", "Independent of the powertrain.", "Truck tasks mixed into engine classes.")),
    (J + "ServicePlanner.java", dwn("Asks every part for its tasks, works out when each is next due, sorts soonest first.",
        "One place for the arithmetic, tested without Spring.", "Each vehicle class computing its own dates differently.",
        "<ul><li><code>Math.ceilDiv(odometer, every) * every</code> is the next multiple, at least one interval.</li></ul>")),
    (J + "Fleet.java", "<p>The five vehicles.</p>"),
    (J + "ServiceTask.java", "<p>A task and its interval.</p>"),
    ("src/main/resources/application.yaml", "<p>Turns on Spring Boot's RFC 9457 problem bodies for every error.</p>"),
    (J + "FleetApplication.java", "<p>Standard Spring Boot entry point.</p>"),
]
tree = """stations/012-fleet-vehicles-abstract-classes-vs-interfaces/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/dakroute/fleet/
│   ├── ServicePlanController.java   ├── ServicePlanner.java   ├── Fleet.java
│   ├── Vehicle.java                 ├── ServiceItems.java     ├── ServiceTask.java
│   ├── Powertrain.java              ├── Body.java             └── FleetApplication.java
├── src/test/java/com/dakroute/fleet/   (see Tests)
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
""" + code("""curl http://localhost:8080/fleet/vehicles/3/service-plan
curl http://localhost:8080/fleet/vehicles/5/service-plan""", "bash") + """
<p>Vehicle 5 is an electric two-wheeler: a combination nobody wrote a class for. Compare its tasks with vehicle 3's.</p>
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>404</code>", "Only vehicles 1 to 5 exist.", "Use one of those ids."],
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>ServicePlanContractTest</code> ({cnt('ServicePlanContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>DeepInheritanceTrapTest</code> ({cnt('DeepInheritanceTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "Arithmetic and all 9 combinations", f"<code>ServicePlannerTest</code> ({cnt('ServicePlannerTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "DeepInheritanceTrapTest.java", "<p>Written first: the class tree hands an EV van an oil change and a petrol bike a diesel filter.</p>"),
    (T + "ServicePlanContractTest.java", "<p>Three different vehicles, exact plans, and the refusals.</p>"),
    (T + "ServicePlannerTest.java", "<p>Due-date arithmetic, and every powertrain with every body.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the whole app through MockMvc.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/dakroute/fleet/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=CngPowertrainChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "A CNG van joins the fleet", "Beginner-friendly", 20,
    "Add a CNG powertrain (oil change every 10,000 km, gas leak check every 10,000 km, cylinder hydro-test every 1,00,000 km) and vehicle 6, a Bajaj Maxima Cargo CNG van, KA01CN2468, at 51,000 km. Count how many files you change.",
    "both tests in <code>CngPowertrainChallengeTest</code> pass: the CNG van's plan is right and vehicle 2's is unchanged.",
    ["Two files: a new enum value and a new fleet entry. With the old class tree it would have been a new class and a fight with its parents.",
     "The station's combination test now covers CNG with every body too, for free."],
    "challenge/CngPowertrainChallengeTest.java", ["challenge/solution/Powertrain.java", "challenge/solution/Fleet.java"]) + challenge(2, "Only what is due soon", "Beginner-friendly", 20,
    "The workshop asks what is due in the next N km. Add an optional <code>withinKm</code> parameter (1 to 1,00,000; the boundary is included).",
    "all three tests in <code>WithinKmChallengeTest</code> pass.",
    ["Filter the planned list; do not touch the planner's arithmetic.",
     "<code>@Min</code>/<code>@Max</code> on a parameter need the validation starter: <code>challenge/solution/pom-additions.xml</code> has the dependency."],
    "challenge/WithinKmChallengeTest.java", ["challenge/solution/ServicePlanController.java", "challenge/solution/pom-additions.xml"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>When is an abstract class the right tool?</h2>
<p>Dakroute's telematics team wants every vehicle tracker to share the same connection, retry and logging code, with each tracker brand filling in how it reads GPS. Sketch it once with an abstract class (a template method) and once with an interface plus a helper class. Which would you choose, and what would make you change your mind?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: the class tree gives the EV van an oil change.</li>
<li>Name the independent parts of a vehicle: powertrain and body.</li>
<li>Write one small interface for what the planner needs, and let both enums implement it.</li>
<li>Compose a vehicle from the two parts; plan by asking each part.</li>
<li>Test every combination, so no part can leak into another.</li>
</ol>
<h2>Abstract class or interface?</h2>
""" + table(["", "Abstract class", "Interface"], [
    ["Holds fields (state)", "Yes", "No (constants only)"],
    ["Shares method code", "Yes", "Only <code>default</code> methods, without state"],
    ["A class can have", "One parent", "Many interfaces"],
    ["Says", "\"is a kind of\"", "\"can do\""],
    ["Good for", "Close relatives sharing state and a fixed sequence of steps", "Any type that can play a role, unrelated or not"]]) + """
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Interface + enums + composition", "A part per independent idea; combinations are free.", '<span class="pill ok">Chosen</span>'],
    ["Deep tree of abstract classes", "Children inherit everything, including later mistakes (the trap).", '<span class="pill bad">Wrong here</span>'],
    ["One class with <code>if (type == ...)</code>", "Every new type edits the same method; station 014 shows where that leads.", '<span class="pill bad">Wrong</span>'],
    ["Abstract class for shared plumbing (template method)", "Right when subclasses truly share state and steps, as in Challenge 3.", '<span class="pill warn">When it fits</span>']]) + """
<h2>Database design</h2>
<p>None in this station. In a database, powertrain and body are two columns (or two small tables) and tasks hang off each; a vehicle row points at one of each.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Maintainability</dt><dd>A new powertrain or body is one enum value. A new kind of rule for every vehicle is one more part in <code>Vehicle.parts()</code>.</dd>
<dt>Correctness</dt><dd>The combination test guards the core promise: a vehicle gets exactly its parts' tasks.</dd>
<dt>Data</dt><dd>Real intervals vary by model and duty; in production they come from data, not code. The structure stays the same.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Abstract class or interface: how do you choose?", "Interface when you describe a role many unrelated types can play; it holds no state and a class can implement many. Abstract class when close relatives share state and a fixed series of steps. When in doubt, start with an interface."),
    ("What does 'favour composition over inheritance' mean?", "Build objects from parts they have, rather than parents they are. Parts can be combined freely and changed independently; a parent's change reaches every child."),
    ("What is the fragile base class problem?", "A change to a parent class silently changes every subclass, including ones the change was never meant for, like a truck task appearing on bikes."),
    ("What is polymorphism here?", "The planner calls tasks() on each part without knowing if it is a powertrain or a body; each answers in its own way."),
    ("Can an enum implement an interface?", "Yes. Each enum value is an object; it can carry data and implement methods, which makes small fixed sets of behaviour very simple."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can say which tests fail if a part is left out."],
    ["Design", "A vehicle is composed of parts.", "You can name a case where an abstract class is the better tool."],
    ["Tests", "Every combination is tested.", "You can explain why that one test replaces nine."],
    ["Explanation", "The table: abstract class against interface.", "You can spot a fragile base class in someone else's code."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any class hierarchy:</p>
<ul class="rules">
<li>Is every subclass truly "a kind of" its parent, for every method it inherits?</li>
<li>How many levels deep is the tree? Could the levels be parts instead?</li>
<li>If you changed the parent, which children would change without asking?</li>
<li>Is there copied code that a shared part could replace?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
