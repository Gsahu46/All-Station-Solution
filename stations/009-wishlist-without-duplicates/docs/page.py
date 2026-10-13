"""Station 009 content. Rendered by curriculum/station_render.py, which provides the helpers
(code, read, run, belongs, table, filebrowser, dwn, e, examples, challenge) and STATION_RUN / N_TESTS from docs/test-run.txt."""

META = {
    "id": 9,
    "stack": "Spring Boot 4.1.1 · Java 25 · Spring MVC · Java records · HashSet / HashMap · MockMvc",
    "simulation": "Five products and two wishlists (7 and 8) are fixed in the code; wishlists live in memory. No login: the wishlist id is in the URL.",
    "readme_requirements": "Needs JDK 25 (or 21, see Set up &amp; code). No Docker, no database. No Maven install: use <code>./mvnw</code> (<code>.\\mvnw.cmd</code> on Windows).",
}
J = "src/main/java/com/kartwala/wishlist/"
T = "src/test/java/com/kartwala/wishlist/"
SP = STATION_RUN[0]
cnt = lambda c: SP[c][1]

# ---------- Level 1: Understand ----------
TERMS = [
    ("SKU", "A product's code.", "The number printed under a barcode.", "<code>PH-12</code>"),
    ("<code>equals</code>", "Java's question \"are these two objects the same thing?\"", "Two printed copies of the same ticket.", "<code>Sku(\"ph-12\")</code> equals <code>Sku(\"PH-12\")</code>."),
    ("<code>hashCode</code>", "A number that says which bucket an object goes in. Equal objects must have equal numbers.", "The shelf number in a library: the same book always goes to the same shelf.", "Comes free with a record."),
    ("HashSet / HashMap", "Collections that find things fast by bucket, then confirm with <code>equals</code>.", "Going straight to shelf 42, then reading the titles there.", "A wishlist is a set of SKUs; the catalogue is a map by SKU."),
    ("Record", "A Java class that only holds data; equals, hashCode and toString come from its fields.", "A filled-in form: two forms with the same entries are the same.", "<code>record Sku(String value)</code>"),
    ("Immutable key", "A key that cannot change after it is created.", "A house number painted in, not chalked.", "Records have no setters."),
    ("Normalise", "Bring values to one standard form before comparing.", "Writing every name in capitals.", "Trimmed and upper-cased in the <code>Sku</code> constructor."),
]
STORY = [
    ("Ravi wishes for a phone three times", "He taps the heart on the search page, the product page and an old version of the app. Each sends the SKU slightly differently: <code>ph-12</code>, <code>PH-12</code>, <code>␠PH-12␠</code>."),
    ("The wishlist shows the phone three times", "The server's SKU class compared case-insensitively in <code>equals</code> but never defined <code>hashCode</code>, so the <code>HashSet</code> put each copy in a different bucket and never compared them."),
    ("The fix", "A record <code>Sku</code> that normalises in its constructor: every spelling becomes <code>PH-12</code> before it is stored, and records give matching <code>equals</code> and <code>hashCode</code>."),
]
understand = belongs(
    ["The real-life problem as a 3-step story", "What we are building, and an everyday analogy", "How it works in 4 steps",
     "One question to check yourself", "What this station is not", "Key terms"],
    "Level 1, about 5 minutes. Plain language: no code.") + """
<h2>The problem in real life</h2>
<ol class="story">""" + "".join(f"<li><strong>{t}</strong><p>{d}</p></li>" for t, d in STORY) + """</ol>
<p class="lesson">A <code>HashSet</code> asks two questions: "which bucket?" (<code>hashCode</code>) and then "same thing?" (<code>equals</code>). If the answers disagree, duplicates get in.</p>

<h2>What are we building?</h2>
<p>A wishlist API: add a product by SKU, read the wishlist, remove a product. However a SKU is spelled, it is in the list once, and the list keeps the order products were added.</p>

<h2>An everyday analogy</h2>
<p>A library shelves books by the first letter of the title. A librarian checks for duplicates only on the shelf where a book belongs. If the shelving rule says "first letter" but the duplicate rule says "same book in any case", then "the hobbit" (shelf t) and "The Hobbit" (shelf T) are never compared, and the library ends up with two. The shelving rule (<code>hashCode</code>) must agree with the duplicate rule (<code>equals</code>).</p>

<h2>How it works in 4 steps</h2>
<ol class="steps">
<li><strong>The app sends a SKU</strong> in any spelling: <code>{"sku": " ph-12 "}</code>.</li>
<li><strong>The <code>Sku</code> record normalises it</strong> to <code>PH-12</code> (or refuses a malformed one with <code>400</code>).</li>
<li><strong>The catalogue is checked</strong>: an unknown product is <code>422</code>.</li>
<li><strong>The wishlist set adds it</strong>: <code>201</code> if new, <code>200</code> if it was already there. Either way, once.</li>
</ol>

<details class="qa check"><summary>Check yourself: a key in a HashSet changes its value after being added. Why can the set no longer find it?</summary><p>The set put it in the bucket for its <em>old</em> hashCode. Looking it up now computes the <em>new</em> hashCode and searches a different bucket. The object is still in the set but cannot be found or removed. That is why keys must be immutable.</p></details>

<h2>What this station is not</h2>
<ul class="scope">
<li><strong>No login and no database.</strong> Two wishlists live in memory.</li>
<li><strong>No prices that change.</strong> The catalogue is fixed.</li>
</ul>

<h2>Key terms</h2>
""" + table(["Term", "Simple meaning", "Everyday example", "In this project"], [[f"<strong>{t}</strong>", m, x, p] for t, m, x, p in TERMS])

# ---------- Level 2: Spec ----------
spec = belongs(["1. Business problem", "2. Acceptance criteria", "3. Requirements", "4. Learning objectives"],
               "Level 2. What a teammate hands you before you build.") + """
<h2>Business problem</h2>
<p><strong>Kartwala</strong> (the marketplace from station 003) sends price-drop alerts to wishlist owners. Some customers got the same alert three times, because the same phone was in their wishlist three times. The SKU arrives in different spellings from different screens and app versions, and the server's SKU class broke the <code>equals</code>/<code>hashCode</code> contract.</p>

<h2>Acceptance criteria</h2>
<ol class="gwt">
<li><b>Given</b> an empty wishlist, <b>when</b> <code>ph-12</code>, <code>PH-12</code> and <code>␠PH-12␠</code> are added, <b>then</b> the wishlist holds <code>PH-12</code> once: <code>201</code>, then <code>200</code>, <code>200</code>.</li>
<li><b>Given</b> several products, <b>then</b> they are listed in the order first added; adding one again does not move it.</li>
<li><b>Given</b> a DELETE in any letter case, <b>then</b> <code>204</code>, and again <code>204</code>.</li>
<li><b>Given</b> a malformed SKU, <b>then</b> <code>400</code> without echoing it. <b>Given</b> an unknown product, <b>then</b> <code>422</code>. <b>Given</b> an unknown wishlist, <b>then</b> <code>404</code>.</li>
</ol>

<h2>Requirements</h2>
<ul class="rules">
<li>A SKU is 2–30 letters, digits or hyphens, starting with a letter or digit; compared after trimming and upper-casing with <code>Locale.ROOT</code>.</li>
<li>Equal SKUs must have equal hash codes; SKUs never change after creation.</li>
<li>Each wishlist is a set that keeps insertion order.</li>
<li>Errors are RFC 9457 problems that never repeat input.</li>
</ul>

<h2>Learning objectives</h2>
<ul>
<li>State the <code>equals</code>/<code>hashCode</code> contract and show what breaks without it.</li>
<li>Use records for value equality and immutable keys.</li>
<li>Normalise in the constructor, so no unnormalised value exists.</li>
<li>Choose <code>HashSet</code>, <code>LinkedHashSet</code> or <code>HashMap</code> for the job.</li>
<li>Use the boolean from <code>Set.add</code> instead of a separate <code>contains</code> check.</li>
</ul>
"""

# ---------- Level 2: API contract ----------
api = belongs(["5. API contract", "Real request/response examples captured from the running app"],
              "Examples are captured with curl from the running app, never typed by hand.") + """
<h2>Endpoints</h2>
""" + table(["Method", "Path", "Purpose"], [
    ["<code>GET</code>", "<code>/wishlists/{id}</code>", "The wishlist: <code>wishlistId</code>, <code>count</code>, <code>items</code> (sku, name, pricePaise)"],
    ["<code>POST</code>", "<code>/wishlists/{id}/items</code>", "Add a product: <code>{\"sku\": \"PH-12\"}</code>. <code>201</code> if added, <code>200</code> if already there."],
    ["<code>DELETE</code>", "<code>/wishlists/{id}/items/{sku}</code>", "Remove a product: <code>204</code>, even if it was not there."]]) + """
<h2>Status codes</h2>
""" + table(["Status", "When"], [
    ['<span class="pill ok">201</span>', "The product was added"],
    ['<span class="pill ok">200</span>', "The product was already in the list (in any spelling); GET"],
    ['<span class="pill ok">204</span>', "Removed (or was not there)"],
    ['<span class="pill warn">400</span>', "Missing or malformed SKU"],
    ['<span class="pill warn">404</span>', "Unknown wishlist"],
    ['<span class="pill warn">422</span>', "Well-formed SKU that is not in the catalogue"]]) + """
<p class="note">Why POST here, after station 008 said POST is not idempotent? Adding to a <em>set</em> is idempotent in effect: the second add changes nothing. The different status (<code>201</code> then <code>200</code>) tells the app whether this request added it.</p>
<h2>Captured examples</h2>
<p class="muted">Captured with curl from the running app on """ + read("docs/captures/date.txt").strip() + """. JSON bodies are indented for reading; <code>Date</code> and connection headers are left out.</p>
""" + examples([
    ("01-add", "Case 1: the search page adds \"ph-12\"", "<b>Why:</b> new to this wishlist: <code>201</code>, stored as <code>PH-12</code>."),
    ("02-add-upper", "Case 2: the product page adds \"PH-12\"", "<b>Why:</b> the same SKU, so the set does not change: <code>200</code>, count still 1."),
    ("03-add-spaces", "Case 3: an old app adds \" PH-12 \"", "<b>Why:</b> trimmed in the constructor before any comparison: still the same SKU."),
    ("04-add-tv", "Case 4: a second product", "<b>Why:</b> a different SKU: <code>201</code>, added after the phone."),
    ("05-unknown-product", "Case 5: a SKU not in the catalogue", "<b>Why:</b> well-formed but no such product: <code>422</code>."),
    ("06-bad-sku", "Case 6: a malformed SKU", "<b>Why:</b> spaces and <code>!</code> are not allowed: <code>400</code> with a fixed message, not the input."),
    ("07-remove", "Case 7: remove in lower case", "<b>Why:</b> <code>ph-12</code> becomes <code>PH-12</code> and is removed: <code>204</code>."),
    ("08-get", "Case 8: what is left", "<b>Why:</b> only the TV."),
])

# ---------- Level 2: Edge cases & trap ----------
trap = belongs(["6. Edge cases and failure cases", "7. The trap, shown failing with a test"],
               "Every edge case points at the test that proves it.") + """
<h2>Edge cases</h2>
""" + table(["Case", "What happens", "Proved by"], [
    ["Three spellings of one SKU", "Stored once", "<code>theRealWishlistKeepsOnePhone</code>"],
    ["Equal SKUs", "Equal hash codes; not equal to a String or null", "<code>equalSkusHaveEqualHashCodes</code>"],
    ["As keys in HashSet and HashMap", "One key per SKU", "<code>aHashSetAndAHashMapTreatThemAsOneKey</code>"],
    ["Turkish server locale", "<code>mi-11x</code> still equals <code>MI-11X</code>", "<code>aTurkishServerLocaleDoesNotChangeTheKey</code>"],
    ["Empty, one letter, space or underscore inside, 31 characters, null", "Refused", "<code>malformedValuesAreRefused</code>"],
    ["Order", "First-added order; re-adding does not move it", "<code>itemsKeepTheOrderTheyWereAdded</code>"],
    ["Two wishlists", "Independent", "<code>wishlistsAreSeparate</code>"],
    ["Remove in another case; remove again", "<code>204</code>, <code>204</code>", "<code>removingIs204InAnyLetterCaseAndAgainIs204</code>"],
    ["Malformed SKU, blank, missing field", "<code>400</code>, not echoed", "<code>aMalformedSkuIs400WithoutEchoingIt</code>"],
    ["Unknown product", "<code>422</code>", "<code>aWellFormedSkuThatIsNotInTheCatalogIs422</code>"],
    ["Unknown wishlist", "<code>404</code>", "<code>anUnknownWishlistIs404</code>"]]) + """
<h2>The trap</h2>
<div class="trap">
<p class="eyebrow">Plausible but wrong</p>
<p class="lead">Overriding <code>equals</code> without <code>hashCode</code>, or using a mutable field as the key.</p>
<p>The "before" <code>OldSku</code> has a careful <code>equals</code>, and a unit test comparing two of them with <code>equals</code> passes. But a <code>HashSet</code> uses <code>hashCode</code> first, and <code>Object.hashCode</code> gives each object its own number, so the three spellings are never compared. The first test shows three phones; the second shows a mutable key getting lost inside a set; the third shows the real API keeping one phone. Removing the upper-casing from <code>Sku</code> was tried while building: 7 tests went red.</p>
</div>
""" + code(read(T + "EqualsWithoutHashCodeTrapTest.java"), "java")

# ---------- Level 2: Set up & code ----------
code_files = [
    (J + "WishlistController.java", dwn("Three endpoints. Turns raw text into a <code>Sku</code> (or <code>400</code>), checks the catalogue (<code>422</code>), adds, and answers <code>201</code> or <code>200</code>.",
        "All HTTP decisions in one place.",
        "No API.",
        "<ul><li><code>wishlists.add</code> returns whether the set changed, which picks the status: no separate <code>contains</code> check that could race.</li></ul>")),
    (J + "Sku.java", dwn("The key: one normalised, validated, immutable value.",
        "A record gives <code>equals</code> and <code>hashCode</code> from the same field, so they always agree; normalising in the constructor means no unnormalised SKU can exist.",
        "Every caller would have to remember to trim and upper-case, and one would forget.")),
    (J + "Wishlists.java", dwn("Holds a <code>LinkedHashSet&lt;Sku&gt;</code> per wishlist.",
        "A set refuses duplicates by itself; \"linked\" keeps the order they were added.",
        "A list, where duplicates need manual checks.")),
    (J + "Catalog.java", dwn("The products, in a <code>Map&lt;Sku, Product&gt;</code>.", "Shows a record used as a map key: lookups by an equal Sku find the product.", "No names or prices in the wishlist.")),
    (J + "ApiErrors.java", "<p>Adds an <code>errors</code> map to validation failures (as in station 004).</p>"),
    (J + "WishlistApplication.java", "<p>Standard Spring Boot entry point.</p>"),
]
tree = """stations/009-wishlist-without-duplicates/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/kartwala/wishlist/
│   ├── WishlistController.java   ├── Sku.java        ├── Wishlists.java
│   ├── Catalog.java              ├── ApiErrors.java  └── WishlistApplication.java
├── src/test/java/com/kartwala/wishlist/   (see Tests)
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
<p>The bodies are in <code>docs/sku-lower.json</code> (<code>ph-12</code>) and <code>docs/sku-upper.json</code> (<code>PH-12</code>).</p>
""" + code("""# Add twice in two spellings: expect 201, then 200
curl -i -X POST http://localhost:8080/wishlists/7/items -H "Content-Type: application/json" -d "@docs/sku-lower.json"
curl -i -X POST http://localhost:8080/wishlists/7/items -H "Content-Type: application/json" -d "@docs/sku-upper.json"

# One phone: "count": 1
curl http://localhost:8080/wishlists/7""", "bash") + """
<h2>Troubleshooting</h2>
""" + table(["You see", "Cause", "Fix"], [
    ["<code>422 Unknown product</code>", "The SKU is not one of the five in <code>Catalog</code>.", "Use PH-12, TV-55, EB-141, MI-11X or CK-5L."],
    ["<code>404</code>", "Only wishlists 7 and 8 exist.", "Use one of those ids."],
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
    ["Every station", "HTTP contract: valid, invalid, not found", f"<code>WishlistContractTest</code> ({cnt('WishlistContractTest')})", '<span class="pill ok">pass</span>'],
    ["Every station", "Reproduce the failure before the fix", f"<code>EqualsWithoutHashCodeTrapTest</code> ({cnt('EqualsWithoutHashCodeTrapTest')})", '<span class="pill ok">pass</span>'],
    ["This station", "The equals/hashCode contract on the key", f"<code>SkuTest</code> ({cnt('SkuTest')})", '<span class="pill ok">pass</span>']]) + """
<h2>Run output</h2>
<p class="muted">JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in <code>docs/test-run.txt</code>.</p>
<pre class="console">""" + e(run_out) + """</pre>
<h2>Test files</h2>
""" + filebrowser("tests", [
    (T + "EqualsWithoutHashCodeTrapTest.java", "<p>Written first: three phones from a broken key; a lost mutable key; one phone with the record.</p>"),
    (T + "SkuTest.java", "<p>The contract checked pair by pair, sets and maps, a Turkish locale, refused values.</p>"),
    (T + "WishlistContractTest.java", "<p>Add, order, separate lists, remove twice, every refusal.</p>"),
    (T + "ApiTest.java", "<p>Shared setup: the whole app through MockMvc, empty wishlists before each test.</p>")])

# ---------- Level 2: Practice ----------
CH_RUN = run("challenge-run.txt")
assert CH_RUN[1] == CH_RUN[2], "the saved challenge run has failures"
practice = belongs(["19. Practice challenges with ready tests and hidden solutions", "One design-on-paper task"],
                   "Every challenge test is run against its solution before the station ships.") + """
<h2>How to do a challenge</h2>
<ol class="steps">
<li>Copy the challenge test from <code>challenge/</code> into <code>src/test/java/com/kartwala/wishlist/</code>.</li>
<li>Run it and watch it fail: <code>./mvnw test -Dtest=MergeGuestWishlistChallengeTest</code></li>
<li>Change the code until it passes, then run <code>./mvnw test</code> to check the other """ + str(N_TESTS) + """ tests.</li>
</ol>
<p class="muted">Checked (<code>docs/challenge-run.txt</code>): with the reference solutions copied in, all """ + str(CH_RUN[2]) + """ tests pass (""" + str(N_TESTS) + """ station tests and """ + str(CH_RUN[2] - N_TESTS) + """ challenge tests).</p>
""" + challenge(1, "Merge a guest wishlist", "Beginner-friendly", 30,
    "A guest's hearts must join their wishlist when they sign in. Add <code>POST /wishlists/{id}/merge</code> with <code>{\"skus\": [...]}</code>: existing items stay first, new ones follow in the order sent, duplicates in any spelling are skipped, and one bad or unknown SKU means nothing is merged.",
    "all three tests in <code>MergeGuestWishlistChallengeTest</code> pass, and the station's tests still pass.",
    ["Turn every string into a <code>Sku</code> and check the catalogue before changing anything: all or nothing.",
     "<code>Set.addAll</code> skips what is already there, and a <code>LinkedHashSet</code> appends the rest in order."],
    "challenge/MergeGuestWishlistChallengeTest.java", ["challenge/solution/WishlistController.java", "challenge/solution/Wishlists.java"]) + challenge(2, "Most-wished products", "Beginner-friendly", 30,
    "Merchandising wants <code>GET /products/most-wished?limit=10</code>: each product with how many wishlists hold it, most first, ties by SKU.",
    "both tests in <code>MostWishedChallengeTest</code> pass.",
    ["Count in a <code>HashMap&lt;Sku, Integer&gt;</code> with <code>merge(sku, 1, Integer::sum)</code>: this works only because <code>Sku</code> has value equality.",
     "Sort entries by value descending, then by key; then <code>limit</code>."],
    "challenge/MostWishedChallengeTest.java", ["challenge/solution/MostWishedController.java", "challenge/solution/Wishlists.java"]) + """
<section class="challenge"><p class="eyebrow">Challenge 3 · design on paper, no code</p>
<h2>Same product, two SKUs</h2>
<p>Kartwala's sellers list the same phone under different SKUs (<code>PH-12</code> from one seller, <code>SAM-M35-BLK</code> from another). Customers want it once in their wishlist. Is that an equality problem or a data problem? Where would you keep the link between the SKUs, and what would the wishlist store?</p>
</section>
"""

# ---------- Level 3: Design ----------
design = belongs(["8. Implementation approach", "9. Design alternatives and trade-offs", "12. Database design (none in this station)"],
                 "Short at Foundations: the choices that matter here.") + """
<h2>Implementation approach</h2>
<ol class="steps">
<li>Write the trap test: equals without hashCode lets three phones in.</li>
<li>Make <code>Sku</code> a record that normalises and validates in its constructor.</li>
<li>Store each wishlist as a <code>LinkedHashSet&lt;Sku&gt;</code>; use <code>add</code>'s boolean for the status.</li>
<li>Test the contract pair by pair, and in real sets and maps.</li>
</ol>
<h2>Design alternatives and trade-offs</h2>
""" + table(["Approach", "What it costs", "Verdict"], [
    ["Record that normalises in its constructor", "Nothing; the canonical value is all that exists.", '<span class="pill ok">Chosen</span>'],
    ["Class with case-insensitive <code>equals</code> and no <code>hashCode</code>", "Duplicates in every hash collection (the trap).", '<span class="pill bad">Wrong</span>'],
    ["Class with matching case-insensitive <code>equals</code> and <code>hashCode</code>", "Works, but every method must remember the rule, and the response shows whichever spelling came first.", '<span class="pill warn">Possible</span>'],
    ["<code>TreeSet</code> with <code>String.CASE_INSENSITIVE_ORDER</code>", "Uses a comparator instead of equals; loses insertion order; ignores spaces only if you trim first.", '<span class="pill warn">Possible</span>'],
    ["Lombok <code>@EqualsAndHashCode</code>", "Generated and consistent, but a dependency for what records already do.", '<span class="pill warn">Not needed</span>']]) + """
<h2>Database design</h2>
<p>None in this station. With a database, the same rule is a primary key <code>(wishlist_id, sku)</code> plus a check that <code>sku = upper(trim(sku))</code>, so a script cannot insert a second spelling.</p>
"""

# ---------- Level 3: Production ----------
prod = belongs(["15. Real-world considerations", "14. Operations (Production Scale stations only)"],
               "A Foundations station: the considerations to know, no runbook.") + """
<dl class="facts">
<dt>Correctness</dt><dd>Every place that compares SKUs gets the same answer, because there is one normalised form. Price-drop alerts go out once per product.</dd>
<dt>Performance</dt><dd>Hash lookups take constant time on average. A broken <code>hashCode</code> that returns the same number for everything is "correct" but turns every set into a slow list.</dd>
<dt>Security</dt><dd>The wishlist id in the URL is a demo shortcut; real apps take it from the login. A malformed SKU is refused with a fixed message.</dd>
<dt>Maintainability</dt><dd>Changing the SKU rule (say, allowing dots) is one pattern in one record.</dd>
</dl>
"""

# ---------- Level 3: Interview ----------
qa = [
    ("What is the equals/hashCode contract?", "If two objects are equal by equals, they must have the same hashCode. (Equal hash codes do not have to mean equal objects.) Hash collections rely on it: they find the bucket with hashCode, then compare with equals."),
    ("What happens if you override equals but not hashCode?", "Equal objects get different hash codes (Object's version), land in different buckets, and are never compared. HashSet keeps duplicates; HashMap lookups by an equal key return null."),
    ("Why must map keys be immutable?", "The bucket is chosen when the key is inserted. If the key's fields change, its hashCode changes, and lookups search the wrong bucket: the entry is still there but cannot be found or removed."),
    ("What do records give you?", "A constructor, accessors, and equals, hashCode and toString based on all components. Fields are final, so records make good keys, as long as their components are immutable too."),
    ("Why normalise in the constructor rather than in equals?", "Then only canonical values exist: equals, hashCode, toString, JSON output and database storage all see the same form, with no rule repeated."),
]
interview = belongs(["16. Interview takeaways", "17. Self-check rubric"], "Answers are hidden until opened, so the learner tries first.") + """
<h2>Interview takeaways</h2>
""" + "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in qa) + """
<h2>Self-check rubric</h2>
""" + table(["Area", "Meets the bar", "Above the bar"], [
    ["Correctness", f"All {N_TESTS} tests pass.", "You can predict which tests fail without the upper-casing."],
    ["Design", "A record key that normalises itself.", "You can compare it with a comparator-based TreeSet."],
    ["Tests", "The contract is tested on real collections.", "You showed a mutable key getting lost, in your own words."],
    ["Explanation", "You can state the contract.", "You can explain buckets to someone new."]])

# ---------- Level 3: Review ----------
review = belongs(["18. Reviewer view (not part of this station)"], "Reviewer views start with stations marked for them in the roadmap.") + """
<h2>No reviewer view for this station</h2>
<p>This Foundations station has no flawed version to review. Use this checklist on any class you see used as a key:</p>
<ul class="rules">
<li>If it overrides <code>equals</code>, does it override <code>hashCode</code> with the same fields?</li>
<li>Can any field used in them change after construction?</li>
<li>Is the value normalised before it is compared, in one place?</li>
<li>Would a record do the same job with less code?</li>
</ul>
"""

LEVELS = [
    ("1", "Understand", [("understand", "Understand", "0", understand)]),
    ("2", "Build", [("spec", "Spec", "1–4", spec), ("api", "API contract", "5", api), ("trap", "Edge cases & trap", "6–7", trap),
                    ("code", "Set up & code", "10–11", codetab), ("tests", "Tests", "13", tests), ("practice", "Practice", "19", practice)]),
    ("3", "Go deeper", [("design", "Design", "8, 9, 12", design), ("production", "Production", "14–15", prod),
                        ("interview", "Interview", "16–17", interview), ("review", "Review", "18", review)]),
]
