"""Station 008 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 8,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · Bean Validation · JSON Merge Patch · MockMvc",
    "simulation": "Two customers (42 and 43) are fixed in the code; addresses live in memory. No login: the customer id is in the URL.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/tiffino/addresses/"
T = "src/test/java/com/tiffino/addresses/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("Idempotent", "Doing it twice leaves things the same as doing it once.", "Switching a light ON: pressing ON again changes nothing.", "PUT, PATCH (as used here) and DELETE."),
    ("PUT", "\"Make the thing at this address exactly this.\"", "Replacing a whole page in a file.", "<code>PUT /customers/42/addresses/home</code>"),
    ("PATCH", "\"Change only these parts.\"", "Correcting one word on the page.", "<code>{\"landmark\": \"Gate 2\"}</code>"),
    ("POST", "\"Add one more.\" Not idempotent: twice adds two.", "Dropping a letter in a post box.", "Not allowed on an address here."),
    ("JSON Merge Patch", "A PATCH format (RFC 7396): fields present replace, <code>null</code> removes, missing ones stay.", "A correction slip: cross out, write over, leave the rest.", "<code>{\"line2\": null}</code> removes line 2."),
    ("204 No Content", "\"Done, nothing to send back.\"", "A nod.", "Every DELETE."),
    ("405 + Allow", "\"That method is not allowed here; these are.\"", "A sign: \"Entry only from the other door.\"", "<code>POST</code> on an address."),
]
STORY = [
    ("Priya edits her home address", "She is on a weak signal in a lift. She taps Save; the server saves it, but the reply never reaches her phone."),
    ("The app tries again", "The old API used <code>POST</code>, which means \"add one more\". The retry adds a second \"home\". At checkout she sees two, and later deleting one shows an error because the other was already gone."),
    ("The fix", "Name the address in the URL and use methods that are safe to repeat: <code>PUT …/addresses/home</code> sets it, <code>DELETE</code> removes it. Doing either twice leaves the same result."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">Phones retry. The question is not whether a request arrives twice, but whether arriving twice does any harm.</p>

<h2>What are we building?</h2>
<p>A saved-addresses API where each address is named by a label in the URL (<code>home</code>, <code>work</code>). <code>PUT</code> sets a whole address, <code>PATCH</code> changes some fields, <code>DELETE</code> removes it. Repeating any of them is harmless.</p>

<h2>An everyday analogy</h2>
<p>A row of labelled letterboxes. "Put this letter in box HOME" twice leaves one letter in HOME, because the second replaces the first. "Drop a letter in the post box" twice sends two letters. <code>PUT</code> is the labelled box; <code>POST</code> is the post box.</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>The label is in the URL</strong>: <code>/customers/42/addresses/home</code>. Every request is about that one address.</li>
<li><strong>PUT</strong> stores the whole address under the label: <code>201</code> if new, <code>200</code> if replaced. Twice: still one address.</li>
<li><strong>PATCH</strong> changes only the fields sent; <code>null</code> removes an optional field. Twice: same result.</li>
<li><strong>DELETE</strong> makes sure the address is gone: <code>204</code> every time, even if it was already gone.</li>
</ol>

<details class="qa check"><summary>Check yourself: Priya's DELETE succeeds, but the reply is lost. The app sends DELETE again. What should it get?</summary><p><code>204</code> again. The goal "home is not saved" is already true, so the retry succeeds without doing anything. If the second DELETE returned an error, the app would show an error screen for something that worked.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No login.</strong> The customer id is in the URL; real apps take it from the signed-in user.</li>
<li><strong>No database.</strong> Addresses live in memory.</li>
<li><strong>No protection against two phones editing at once.</strong> The last save wins; Practice challenge 1 adds the fix.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Tiffino</strong> (the food-delivery app from station 002) lets customers save delivery addresses. The API saves every edit with <code>POST /customers/{id}/addresses</code>, which adds a new entry. On flaky mobile networks the app retries, so customers end up with two or three copies of "home", and riders sometimes go to an old one. Deleting a duplicate a second time shows an error screen. Support tickets about "wrong address" are the top complaint in Bengaluru.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> a new label, <b>when</b> the app PUTs an address, <b>then</b> <code>201</code> with <code>Location</code>. <b>When</b> it PUTs the same again, <b>then</b> <code>200</code>, the same body, and still one address.</li>
<li><b>Given</b> a saved address, <b>when</b> the app PUTs a different address, <b>then</b> it replaces the whole address: fields left out are gone.</li>
<li><b>Given</b> a PATCH, <b>then</b> only the fields sent change; <code>null</code> removes an optional field; removing a required field is <code>400</code> and changes nothing.</li>
<li><b>Given</b> a DELETE, <b>then</b> <code>204</code>, and a second DELETE is <code>204</code> too.</li>
<li><b>Given</b> a POST to an address, <b>then</b> <code>405</code> with an <code>Allow</code> header listing GET, PUT, PATCH and DELETE.</li>
<li><b>Given</b> 10 saved addresses, <b>when</b> an 11th label is PUT, <b>then</b> <code>409</code>; replacing an existing one still works.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>Labels: 1–20 lower-case letters, digits or hyphens; <code>HOME</code> and <code>home</code> are the same label (<code>Locale.ROOT</code>).</li>
<li>Address fields: <code>line1</code>, <code>city</code>, <code>pincode</code> (6 digits, not starting with 0) required; <code>line2</code>, <code>landmark</code> optional.</li>
<li>PATCH uses JSON Merge Patch (<code>application/merge-patch+json</code>; plain JSON is accepted too). Only the five fields may be patched.</li>
<li>No timestamps or counters in the stored address, so the same request always leaves exactly the same state.</li>
<li>Errors are RFC 9457 problems that never repeat input.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>Choose between PUT, PATCH and POST, and explain which are idempotent.</li>
<li>Design URLs so that a retry targets the same resource.</li>
<li>Implement JSON Merge Patch, including <code>null</code> as "remove".</li>
<li>Return <code>204</code> for DELETE, and <code>405</code> with <code>Allow</code>.</li>
<li>Write replay tests: the same request twice gives one effect.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose", "Idempotent?"], [
    ["<code>GET</code>", "<code>/customers/{id}/addresses</code>", "All saved addresses, by label", "Yes (and safe: changes nothing)"],
    ["<code>GET</code>", "<code>/customers/{id}/addresses/{label}</code>", "One address", "Yes (safe)"],
    ["<code>PUT</code>", "<code>/customers/{id}/addresses/{label}</code>", "Create or replace the whole address", "Yes"],
    ["<code>PATCH</code>", "<code>/customers/{id}/addresses/{label}</code>", "Change some fields (Merge Patch)", "Yes, for this kind of patch"],
    ["<code>DELETE</code>", "<code>/customers/{id}/addresses/{label}</code>", "Make sure it is gone", "Yes"],
    ["<code>POST</code>", "<code>/customers/{id}/addresses/{label}</code>", "Not supported: <code>405</code>", "(POST is not idempotent)"]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "PUT created a new label; <code>Location</code> names it"],
    ['<span class="pill ok">200</span>', "PUT replaced, PATCH changed, GET read"],
    ['<span class="pill ok">204</span>', "DELETE, whether or not the address existed"],
    ['<span class="pill warn">400</span>', "Invalid label, field, or patch (unknown field, non-text value, removing a required field)"],
    ['<span class="pill warn">404</span>', "Unknown customer; GET or PATCH of a label with no address"],
    ['<span class="pill warn">405</span>', "POST on an address; <code>Allow</code> lists the methods that work"],
    ['<span class="pill warn">409</span>', "An 11th label"]]) + """
<p class="note"><strong>Same state, not always the same status.</strong> Idempotency (RFC 9110) is about the effect on the server. A repeated PUT answers <code>200</code> where the first answered <code>201</code>, and that is fine: the address is the same. This API also chose <code>204</code> for a repeated DELETE; returning <code>404</code> (as station 005 did) would also be idempotent, but it turns a successful retry into an error screen.</p>
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-put-new", "Case 1: save \"home\"", "<b>Why:</b> no address had this label: <code>201</code>, and <code>Location</code> is the URL that was used."),
    ("02-put-again", "Case 2: the app's retry", "<b>Why:</b> the same address under the same label: replaced by itself. <code>200</code>, same body, still one address."),
    ("03-patch", "Case 3: change the landmark, remove line 2", "<b>Why:</b> Merge Patch: <code>landmark</code> is replaced, <code>line2: null</code> removes it, everything else stays."),
    ("04-list", "Case 4: all addresses", "<b>Why:</b> one \"home\", whatever the retries did."),
    ("05-post", "Case 5: an old app version POSTs", "<b>Why:</b> POST would mean \"add one more\", which is the bug. <code>405</code>, and <code>Allow</code> tells the client what does work."),
    ("06-bad-pincode", "Case 6: a 5-digit PIN code", "<b>Why:</b> <code>400</code>, naming the field; nothing is saved."),
    ("07-delete", "Case 7: delete \"home\"", "<b>Why:</b> <code>204</code>: gone, nothing to send back."),
    ("08-delete-again", "Case 8: the delete's retry", "<b>Why:</b> already gone, so the goal is met: <code>204</code> again, no error screen."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What the API does", "Proved by"], [
    ["Same PUT three times", "One address; same body each time; <code>201</code>, <code>200</code>, <code>200</code>", "<code>theSamePutThreeTimesLeavesOneIdenticalAddress</code>"],
    ["Same PATCH twice", "Same state", "<code>theSamePatchTwiceLeavesTheSameAddress</code>"],
    ["DELETE twice", "<code>204</code> both times", "<code>deletingTwiceIs204BothTimes</code>"],
    ["Retries on two labels", "Each label independent", "<code>retriesOfDifferentLabelsDoNotTouchEachOther</code>"],
    ["PUT with fewer fields", "Left-out fields are removed (PUT replaces)", "<code>putReplacesTheWholeAddressSoLeftOutFieldsAreGone</code>"],
    ["<code>OFFICE</code> on a Turkish server", "Same label as <code>office</code>", "<code>labelsIgnoreLetterCaseEvenOnATurkishServer</code>"],
    ["Bad label, PIN code starting with 0, blank line 1", "<code>400</code>", "<code>anInvalidLabelOrBodyIs400</code>"],
    ["PATCH one field; <code>null</code> on an optional field", "Only that field changes / is removed", "<code>patchChangesOnlyTheFieldsSent</code>, <code>patchWithNullRemovesAnOptionalField</code>"],
    ["PATCH <code>city: null</code>", "<code>400</code>; nothing changes", "<code>patchCannotRemoveARequiredFieldAndChangesNothing</code>"],
    ["PATCH unknown field, an array, a number for pincode", "<code>400</code>; the field name is not echoed", "<code>patchWithAnUnknownFieldOrANonObjectIs400WithoutEchoingIt</code>"],
    ["PATCH a label with no address", "<code>404</code>", "<code>patchingAnAddressThatDoesNotExistIs404</code>"],
    ["POST on an address", "<code>405</code> + <code>Allow</code>", "<code>postIs405AndTheAllowHeaderListsWhatWorks</code>"],
    ["Unknown customer", "<code>404</code>", "<code>anUnknownCustomerIs404</code>"],
    ["11th label; replacing at the limit", "<code>409</code>; <code>200</code>", "<code>theEleventhLabelIs409ButReplacingAnExistingOneStillWorks</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Using POST for edits, so a retry on a flaky network creates duplicates.</p>
<p>"Save address" feels like "create", so POST feels natural, and it works on office Wi-Fi. The first test sends the same POST twice, as an app does after a lost reply, to the "before" API: two addresses. The second sends the same PUT twice to the real API: one. Removing <code>Locale.ROOT</code> from the label was tried while building: the Turkish-locale test went red.</p>
</div>
""" + code(read(T + "PostForEditsTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "AddressController.java", dwn("Maps GET, PUT, PATCH and DELETE on <code>/customers/{id}/addresses/{label}</code>, normalises the label, and validates patched results.",
        "The label in the URL makes every request target one known address, which is what makes retries safe.",
        "No API.",
        "<ul><li>No <code>@PostMapping</code>: Spring itself answers POST with <code>405</code> and <code>Allow</code>.</li><li>A PATCH is validated <em>after</em> merging, because the rules apply to the result, not to the patch.</li></ul>")),
    (J + "MergePatch.java", dwn("Applies a JSON Merge Patch to an address: present replaces, <code>null</code> removes, missing stays.",
        "One small, testable rule for partial updates.",
        "Clients would have to send the whole address to change one field, and two phones would overwrite each other's untouched fields.",
        "<ul><li>Error messages list the allowed fields instead of repeating the one sent.</li></ul>")),
    (J + "AddressBook.java", dwn("Keeps each customer's addresses in a map keyed by label.",
        "A map cannot hold two \"home\" entries: putting again replaces.",
        "A list, where every save appends (the trap).")),
    (J + "Address.java", dwn("The address and its rules. Trims text; a blank optional field becomes <code>null</code>.",
        "\"\" and a missing landmark are the same address, so retries with slightly different JSON still give the same state.",
        "Invalid addresses get saved.")),
    (J + "ApiErrors.java", "<p>Adds an <code>errors</code> map to validation failures (as in station 004).</p>"),
    (J + "AddressesApplication.java", "<p>Standard Spring Boot entry point.</p>"),
]
tree = """stations/008-saved-delivery-addresses/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/tiffino/addresses/
│   ├── AddressController.java   ├── MergePatch.java   ├── AddressBook.java
│   ├── Address.java             ├── ApiErrors.java    └── AddressesApplication.java
├── src/test/java/com/tiffino/addresses/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     address.json, patch.json, capture script, captures, saved runs"""
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
""" + code("""# Save twice: expect 201, then 200
curl -i -X PUT http://localhost:8080/customers/42/addresses/home -H "Content-Type: application/json" -d "@docs/address.json"
curl -i -X PUT http://localhost:8080/customers/42/addresses/home -H "Content-Type: application/json" -d "@docs/address.json"

# Patch: new landmark, no line 2
curl -i -X PATCH http://localhost:8080/customers/42/addresses/home -H "Content-Type: application/merge-patch+json" -d "@docs/patch.json"

# Still one address
curl http://localhost:8080/customers/42/addresses

# Delete twice: expect 204 both times
curl -i -X DELETE http://localhost:8080/customers/42/addresses/home
curl -i -X DELETE http://localhost:8080/customers/42/addresses/home""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>415</code> on PATCH", "Missing or wrong <code>Content-Type</code>.", "Use <code>application/merge-patch+json</code> or <code>application/json</code>."],
    ["<code>405</code>", "POST instead of PUT.", "Addresses are set with PUT."],
    ["<code>release version 25 not supported</code>", "Maven is using an older JDK.", "Point <code>JAVA_HOME</code> at JDK 25, or add <code>-Djava.version=21</code>."]]) + """
<h2>Project layout</h2>
<pre class="tree">""" + e(tree) + """</pre>
<h2>Code walkthrough</h2>
<p class="muted">In the order a request travels.</p>
""" + filebrowser("code", code_files)

# ---------- Level 2: Tests ----------
run_out = "\n".join(l for l in STATION_RUN[3].splitlines() if "Tests run:" in l or "BUILD" in l)
tests = belongs(["13. Testing: each required test named, with what it proves", "Real run output"],
                "Required tests come from the station's types. The validator fails a station that is missing any of them.") + """
<h2>Required tests for this station</h2>
<p>Station type: <span class="chip">Idempotency</span></p>
""" + table(["Required by", "Requirement", "Test class", "Result"], [
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>AddressContractTest</code> ({cnt('AddressContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>PostForEditsTrapTest</code> ({cnt('PostForEditsTrapTest')})", '<span class="pill ok">pass</span>'],
    ["Idempotency", "Replay: the same request twice gives one effect", f"<code>AddressReplayTest</code> ({cnt('AddressReplayTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "PostForEditsTrapTest.java", "<p>Written first: a retried POST makes two addresses; a retried PUT keeps one.</p>"),
    (T + "AddressReplayTest.java", "<p>Each method repeated: the state after twice equals the state after once.</p>"),
    (T + "AddressContractTest.java", "<p>Every method and status code, Merge Patch rules, <code>405</code> + <code>Allow</code>, the limit.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the whole app through MockMvc, empty address books before each test.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/tiffino/addresses/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=ConditionalUpdateChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Two phones, one address", "Go deeper", 45,
    "Priya and her husband edit \"home\" on two phones. Today the last save silently wins. Return an <code>ETag</code> with GET, PUT and PATCH; when a save sends <code>If-Match</code> with an old ETag, refuse it with <code>412 Precondition Failed</code> and change nothing. Saves without <code>If-Match</code> keep working.",
    "all four tests in <code>ConditionalUpdateChallengeTest</code> pass, and the station's tests still pass.",
    ["The ETag is a fingerprint of the content: the same address must always give the same ETag.",
     "<code>ResponseEntity.ok().eTag(…)</code> sets the header, quotes included.",
     "Check and save in one step (<code>synchronized (book)</code>), or another save can slip in between."],
    "challenge/ConditionalUpdateChallengeTest.java", ["challenge/solution/AddressController.java"]) + challenge(2, "The default address", "Beginner-friendly", 30,
    "Add <code>PUT /customers/{id}/default-address</code> with <code>{\"label\": \"home\"}</code> and <code>GET</code> for it. There is one default at a time; setting it twice gives the same answer; a label with no address is <code>409</code>; deleting the default address clears it (<code>404</code> on GET).",
    "all four tests in <code>DefaultAddressChallengeTest</code> pass.",
    ["Model the default as its own small resource, not a flag on every address: then \"only one default\" is automatic.",
     "Clear it inside <code>delete</code>, so it can never point at a deleted address."],
    "challenge/DefaultAddressChallengeTest.java", ["challenge/solution/DefaultAddressController.java", "challenge/solution/AddressBook.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>"Add a tip" is not idempotent</h2>
<p>Product wants <code>PATCH /orders/{id}</code> with <code>{"addTip": 20}</code>. Why is that PATCH not idempotent, and what happens on a retry? Redesign it two ways: as an idempotent PUT of the total tip, and with an idempotency key (station 085). Which would you choose for a payment-related field, and why?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: a retried POST makes two addresses.</li>
<li>Put the label in the URL, so a request names its address.</li>
<li>Store addresses in a map by label; PUT replaces.</li>
<li>Add Merge Patch, validating the merged result.</li>
<li>Make DELETE return <code>204</code> whether or not the address existed; write a replay test per method.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Client-chosen label in the URL + PUT", "Clients must pick a label; good for a short list like addresses.", '<span class="pill ok">Chosen</span>'],
    ["POST to a collection for every save", "Each retry adds a copy (the trap).", '<span class="pill bad">Wrong</span>'],
    ["POST to create, PUT/PATCH by server id to edit", "Creation still duplicates on retry unless you add an idempotency key (station 085).", '<span class="pill warn">With a key</span>'],
    ["JSON Patch (RFC 6902): a list of operations", "More powerful (move, test, array edits) and more complex; some operations are not idempotent.", '<span class="pill warn">When needed</span>'],
    ["DELETE answers 404 when already gone", "Also idempotent; the retry shows an error screen. Station 005 chose this for bookings.", '<span class="pill warn">Valid choice</span>'],
    ["Store <code>updatedAt</code> on each save", "Useful for audit, but then the same PUT twice changes state; keep it out of the compared state or out of the response.", '<span class="pill warn">Mind the trade-off</span>']]) + """
<h2>Database design</h2>
<p>None in this station. With a database, the primary key <code>(customer_id, label)</code> enforces "one home", and PUT becomes an upsert: <code>INSERT … ON CONFLICT (customer_id, label) DO UPDATE</code>.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Reliability</dt><dd>Idempotent methods let apps, proxies and libraries retry safely. Some HTTP clients and proxies retry idempotent methods automatically but, by default, not POST.</dd>
<dt>Concurrency</dt><dd>Idempotent does not mean conflict-free: two phones with different edits still overwrite each other. Challenge 1 adds <code>ETag</code>/<code>If-Match</code>.</dd>
<dt>Security</dt><dd>The customer id in the URL is a demo shortcut; real APIs take it from the login, or anyone can edit anyone's addresses. Addresses are personal data: do not log them.</dd>
<dt>Maintainability</dt><dd>The rules for an address live in one record; PUT and PATCH both end in the same validation.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("Which HTTP methods are idempotent?", "GET, HEAD, OPTIONS, PUT and DELETE are defined as idempotent by RFC 9110. POST is not. PATCH is not guaranteed: it depends on the patch (\"set landmark\" is, \"add 20 to tip\" is not)."),
    ("PUT or PATCH?", "PUT replaces the whole resource with the body, so fields left out are removed. PATCH changes only what the patch describes. Use PUT when the client has the full state, PATCH for small changes."),
    ("What does null mean in a JSON Merge Patch?", "Remove that field. A field left out of the patch is unchanged. That is why Merge Patch cannot set a field to JSON null: null always means remove."),
    ("Should a second DELETE return 204 or 404?", "Both are idempotent: the server state is the same. 204 makes retries invisible to users; 404 tells the client it was already gone. Pick one, document it, and test it."),
    ("Why is POST on /addresses/home a 405 and not a 404?", "The URL exists; the method is not supported on it. 405 with an Allow header tells the client which methods do work."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can say which replay test fails if addresses are kept in a list."],
    ["Design", "Label in the URL; no POST for edits.", "You can explain when POST plus an idempotency key is better."],
    ["Tests", "A replay test per method.", "You compared whole states, not just status codes."],
    ["Explanation", "PUT against PATCH in one sentence each.", "You can explain why idempotent is not the same as conflict-free."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any write endpoint you review:</p>
<ul class="rules">
<li>If this request arrives twice, what changes the second time?</li>
<li>Is POST used for something that should be PUT?</li>
<li>Does a repeat DELETE give an answer the client can live with?</li>
<li>Does the stored state include anything that changes on every save (time, counters)?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
