# LOG

## 2026-10-09T18:50Z · S0 · HARD BLOCKER
- reference/ unzipped from Product_target_clarification_needed.zip (1160 files). Read-only.
- VISION.md: NOT FOUND (not attached; grep of the zip for the brief's title/"0-3 years"/"Interview Takeaways" found nothing). §6 hard blocker → stopped.
- Env: OpenJDK 21.0.12.1, Maven 3.9.11, Python 3.13.16, docker CLI present but no daemon (Testcontainers will skip), Chromium at /opt/pw-browsers. Web not yet checked.
- Not done: Spring Boot version pin, hello-world build. Resume S0 once VISION.md is in WORK/.

## 2026-10-09T18:47Z · S0 · DONE (resumed after VISION.md arrived)
- VISION.md copied into WORK; LOOP_PROMPT.md copied too so later iterations can re-read it from disk.
- Spring Boot pinned to 4.1.1: newest GA in Maven Central metadata (4.2.0-M2 is a milestone, skipped). Hello-world with spring-boot-starter-webmvc + webmvc-test: mvn verify PASS, 1 test, 0 failures.
- Boot 4 is a new major vs the site's 3.5.x → differences noted once in RUNNING.md (verified items only).
- Env: JDK 21 ✓ Maven ✓ Python ✓ Docker ✗ (CLI, no daemon) web ✓ (Maven Central reachable; WebSearch/WebFetch tools present) browser ✓ (Chromium in /opt/pw-browsers).

## 2026-10-09T18:58Z · S1 · DONE
- discovery.md written with file:line evidence; curriculum/old_stations.json (titles, concepts, packages, companies + banned names/package roots).
- Corrections to the prompt's facts: Thread.sleep in src/test of 19 stations (not 18, 45 was missed); "station N" prose refs = 424 (not ~330); edgeQ needs {t,s,q} (+w,wl,n), not only t; CI has no Java job yet (placeholder only).
- New findings: Approach tab is regex-derived, not data → new teaching fields need viewer changes; viewer hard-codes code-note labels by old station id (6812-6817); 5 colour arrays + PHASES have exactly 10 entries; local mode (SB_ON false) needs no login → no gate patch for render checks; download resolves to data/projects/station-NNN.zip locally.
- Gaps vs VISION §4: no JDBC-first lesson, no PostgreSQL, no quick-commerce storyline, weak Compose/CI/pooling/SOLID/locks.

## 2026-10-09T19:15Z · S2 · iteration 1 of ≤3 · roadmap DRAFT saved
- Human message "I approve" (00:26 IST) arrived before any roadmap existed → logged as approval of the S1 direction (count by coverage; viewer edits above 100 accepted). The PAUSE_AFTER_ROADMAP review still happens.
- Research: 6 searches, 3 pages opened (sources.jsonl). Key facts: Spring Cloud GA supports Boot 4.0.x only (2026.0 is M1); springdoc 3.1.1 supports Boot 4; only resilience4j-spring-boot3 on Central. Recorded as stack risks in roadmap notes; never mix Boot versions.
- Draft: 110 stations, 11 phases, bands 33/33/44, 5 storylines (Basketo, Rydo, Tijori, Plancraft, Dakroute) + 4 standalone companies. Prerequisites derived from «slug» refs; fixed drift (97/98 swapped, 106, 109).
- Next iteration: phases.json, coverage.json, originality.md, old-to-new.json, tools/validate_roadmap.py; then the gate, CURRICULUM.md and the pause.

## 2026-10-09T19:25Z · S2 · iteration 2 · DONE, roadmap LOCKED and APPROVED
- Wrote phases.json (11), coverage.json (all 56 VISION §4 bullets), old-to-new.json (100 old ids; 3 null with reasons: HATEOAS, WebSocket/SSE, GraphQL; 4 partial), originality.md, CURRICULUM.md.
- tools/validate_roadmap.py: PASS. First run caught a real error (config management introduced at 14, not 89), fixed. Negative test on a broken copy: 7 problems reported, exit 1.
- Approval: human wrote "Ok go on don't stop" (00:34 IST) after seeing the S2 summary → treated as explicit approval to skip PAUSE_AFTER_ROADMAP. roadmap_approved = true. Trade-off: the human approved the plan summary, not the 110-row table; CURRICULUM.md is there to review at any time, and rows not yet built can still be changed (with a LOG reason).

## 2026-10-09T19:45Z · S3 · DONE · tooling
- tools/stationlib.py (file walk, source hash, tree, word count), verify_station.sh (mvn -B -ntp -q clean verify → verify.log + verify.json with surefire/failsafe counts and source hash; -q prints nothing on success, so the script appends its own BUILD SUCCESS/FAILURE line from the exit code + test reports), validate_station.py (16 rule codes), export_station.py (files/tree from disk, «slug» → #/station/n links, phase JSON, index.json, deterministic zip, README), fixtures/make_fixtures.py, test_validators.py.
- Gate: test_validators PASS — clean fixture verified by Maven (1 test) and passes validate + export; broken fixture trips 16/16 rules, each for its planted defect.
- Rules added beyond §5 (logged so they can be reverted): R05 0-1 stations need ≥40% basic Q&A (old weakness: 23%); R14 flags double/float fields named like money; R16 «later-slug» allowed only in evolution/company.
- Viewer note for S4: index.json rows carry extra keys yoe, slug (harmless to the current viewer).

## 2026-10-09T20:00Z · S4 · pilot unit 1 · station 001 store-status-lookup COMMITTED
- 12 files (5 main, 3 test, pom, yml, requests.http, README). mvn verify PASS: 14 run / 0 failed / 0 skipped (no Docker needed). validate_station PASS. export PASS.
- Root causes fixed during the gate: (1) Spring Framework 7 standaloneSetup only registers @Controller classes → broken "mistake" controllers are nested @RestController classes in the test; the full @SpringBootTest passing proves Boot's test filter keeps them out of the app. (2) A comment "// ...and gets" tripped R08 (elision marker) → reworded, rule kept.
- Cold README read: Approach referenced "Examples" that the README lacked → exporter now renders an Examples section (all stations). Viewer markdown has no _italics_ → exporter writes *italics*.
- Render check (headless Chromium on a scratch copy, local mode): 7/7 tabs have content, no undefined/NaN/«slug», no console errors, download works (station-001.zip, 9.5 KB). Screenshots checked by eye: Problem, Approach, Code, Interview.
- Viewer gaps recorded in INTEGRATION_NOTES.md (approach/objectives/examples/walkthrough/testing/evolution/takeaways/yoe/verification not shown yet). Verified versions recorded: Jackson 3.1.5 (tools.jackson), Spring Framework 7.0.9, Tomcat 11.0.24, JUnit 6.0.3.
- Tools added: render_site.sh, render_check.py.

## 2026-10-09T20:35Z · S4 · pilot unit 2 · station 067 redis-cache-aside COMMITTED · S4 DONE
- 17 files: 6 main, 5 test, pom, yml, docker-compose.yml, .env.example, requests.http, README. mvn verify PASS: 18 run / 0 failed / 1 skipped (ProductCacheRedisTest, Testcontainers, no Docker). validate PASS, export PASS, render check PASS (7/7 tabs, download OK); station 1 re-checked PASS.
- Root causes fixed: (1) Mockito `any()` was ambiguous between ValueOperations.set(K,V,Duration) and the new set(K,V,Consumer<SetSpec>) → typed matcher. (2) Gap: with the only @SpringBootTest skipped, real wiring (JsonMapper bean, StringRedisTemplate) was unproven → added RedisDownApplicationTest (full app, Redis on port 1) which runs without Docker and proves the outage path. (3) The 404 example claimed a `type` field; printing the real body showed Spring omits type=about:blank → example corrected and the absence pinned by a test.
- Verified Boot 4.1.1 coordinates: spring-boot-starter-data-redis(-test), spring-boot-testcontainers, org.testcontainers:testcontainers-junit-jupiter (TC 2.0.5), Lettuce 7.5.2; Boot 4 auto-configures a tools.jackson JsonMapper bean.
- Honesty: ProductCatalog is an in-memory stand-in for the PostgreSQL catalog; the station says so in `database` and the problem text.

## 2026-10-09T21:05Z · S5 · station 002 catalog-browse-filters COMMITTED
- 12 files (5 main, 3 test). mvn verify PASS 20 run / 0 skipped. validate PASS, export PASS, render check PASS.
- Proven by test, not asserted: Spring Boot's default error body over real HTTP has timestamp/status/error/path and NOT the ResponseStatusException reason (ClientSeesThisErrorTest) → sets up consistent-error-responses.
- R08 caught "// ...then cut" again → reworded (rule kept; comment style note for future stations: never start or end a comment with "...").
- Fixed across stations: examples with money were emitted as floats (35.0) by the Python authoring scripts, while the API sends BigDecimal text (35.00). Money examples now hold exact JSON text; exporter prints string responses verbatim. Stations 2 and 67 re-exported.

## 2026-10-09T21:30Z · S5 · station 003 cart-add-item COMMITTED
- 14 files (7 main, 3 test). mvn verify PASS 20 run / 0 skipped. validate PASS, export PASS, render check PASS.
- Planned bug "missing int becomes 0" was FALSE on this stack: the test failed (400). Read the log: Jackson 3 defaults FAIL_ON_NULL_FOR_PRIMITIVES=true. Bug rewritten to the true behaviour (parse error with no field name; Jackson 2 gave 0) and recorded in RUNNING.md. Correctness over the plan.
- Added a real-HTTP test so the 400 example (default body, no field details) is proven, not assumed.

## 2026-10-09T22:05Z · S5 · station 004 consistent-error-responses COMMITTED
- 21 files (14 main, 3 test). mvn verify PASS 25 run / 0 skipped (incl. an 8-case parameterized "same shape" test). validate PASS (after adding a "how a client should read errors" section: concepts were 629 < 700 words), export PASS, render PASS.
- Examples captured from the packaged app with curl, not written by hand. Observed: Jackson 3 writes ProblemDetail keys alphabetically; Spring fills `instance` automatically; type=about:blank is omitted; real Content-Type is exactly application/problem+json.
- Authoring scripts moved from scratchpad into WORK/authoring/ (not shipped) so later audit fixes can regenerate station.json.
- Standard from here: every later station uses this error shape (ApiException + advice extending ResponseEntityExceptionHandler, types under https://api.basketo.example/problems/ or the station company's equivalent).

## 2026-10-09T22:40Z · S5 · station 005 cart-change-and-remove COMMITTED
- 24 files: 15 main (errors package reused unchanged from 004 + EmptyPatchException; size follows the problem, above the compact guide of 4–8), 3 test. mvn verify PASS 23 run / 0 skipped. validate PASS (concepts +"safe vs idempotent" section: 321 → >350 words), export PASS, render PASS.
- Design correction while scaffolding: empty PATCH is 400 (request can never succeed), not 409; got its own EmptyPatchException.
- Real responses captured from the jar: 405 Allow = "DELETE, GET, PATCH, PUT"; OPTIONS Allow = "DELETE,GET,HEAD,PATCH,PUT,OPTIONS". Three examples (POST twice, GET cart, checkout) were composed from the verified CartLine/CartView JSON format rather than captured; their numbers follow the tested arithmetic.

## 2026-10-09T23:05Z · S5 · station 006 cart-line-dedup COMMITTED
- 19 files (12 main incl. 4 reused error classes; 3 test). mvn verify PASS 18 run / 0 skipped. validate PASS, export PASS, render PASS. Examples captured from the running jar.
- Gate fixes: R08 caught "// two different objects..." comment style (third time; style rule for myself: never use "..." in comments); concepts +"== is not equals" (324 → >350 words).
- Honest scope note in evolution: the per-product limit from 004 is left out here to keep the focus on identity.

## 2026-10-09T23:45Z · S5 · station 007 fare-estimate-policies COMMITTED
- 22 files (14 main, 4 test). mvn verify PASS 35 run / 0 skipped. validate PASS (concepts +2 sections: 581 → >700), export PASS, render PASS. Examples captured from the running jar.
- Validator rule change (logged per §6): R14 "money in double" no longer scans files under /mistakes/, where bug reproductions use double on purpose. test_validators PASS (16/16) and validate_station --all re-run: all committed stations PASS.
- Verified, not assumed: (1) constructor binding of a query record skips Bean Validation when any value fails conversion → only format errors come back first; taught as an edge case and pinned by two tests. (2) 14.3*7 in double prints 100.10000000000001 in Java (shortest-repr printing since JDK 19); my first example (13.1*3) was wrong and failed the test. (3) AssertJ's anyMatch asserts, it does not return a boolean (test fixed).
- Error handler improvement carried forward: binding failures report "has the wrong format" instead of Spring's conversion text.

## 2026-10-10T00:10Z · S5 · station 008 order-history-pages COMMITTED
- 18 files (11 main, 3 test). mvn verify PASS 20 run / 0 skipped. validate PASS (concepts +type erasure: 334 → >350), export PASS, render PASS. Examples captured from the running jar.
- Verified: Jackson 3 writes Instant as ISO-8601 strings ("2026-09-30T11:00:00Z") with no extra configuration.

## 2026-10-10T00:45Z · S5 · station 009 otp-request-limiter COMMITTED
- 17 files (8 main, 6 test). mvn verify PASS 42 run / 0 skipped (incl. a 64-thread latch test repeated 20×; no Thread.sleep anywhere). validate PASS (concepts +visibility +personal data: 610 → >700), export PASS, render PASS. Examples captured from the running jar.
- Design flaw found by timing the tests, then fixed: eviction ran on every request once >10,000 numbers were tracked (O(n) per request, 2.9 s for 20k requests). Now throttled to once a minute with AtomicReference.compareAndSet; a test proves 1 scan for 20,000 requests (0.17 s).
- Race demonstrations are deterministic: CyclicBarrier between check and act, so the bug test cannot be flaky (old-curriculum weakness avoided).
- Standard updated: ApiException.headers() hook so the shared handler can send headers such as Retry-After.

## 2026-10-10T11:30Z · S5 · station 010 request-id-and-logging COMMITTED
- Interrupted mid-iteration: Bash was unavailable (permission classifier timeouts) after the station 10 scaffold attempt; no command ran. Sources, tests and the content script were written with the file tool; the environment then restarted. On resume the workspace was intact (STATE.json, 9+1 committed stations) and nothing needed reconciling: station 10 had no verify.log yet.
- 19 files (11 main, 4 test). mvn verify PASS 16 run / 0 skipped on the first build, including LogLinesTest, which reads the real console output via OutputCaptureExtension. validate PASS (concepts trimmed 535 → ≤500 for compact), export PASS, render PASS.
- Examples captured from the running jar into authoring/captured/s010.json, including the three real log lines for a 404, as support would find them.
- Phase 1 (001–010) complete → next unit: S6 phase 1 audit.

## 2026-10-10T12:40Z · S6 · phase 1 audit (001–010) DONE
- Independent review of all 10 stations; every claim checked against code and tests. Findings fixed (each fix re-ran that station's gates):
  - 010 (false claim, verified by probe): interceptors DO run for unknown paths in a real Boot app (static-resource handler matches); only a 405 skips them. Bug 3 re-taught with InterceptorReachTest; malformed AWBs are no longer logged raw (UntrustedPathLoggingTest). verify PASS 18 run.
  - 009 (false claim): a fixed window's worst burst is 5 in one second, not "6 in a minute"; problem text now says the window starts at the first request. Test worstCaseBurstIsFiveWithinOneSecond added; RateLimitedException detail built from the real limit/window. verify PASS 43 run.
  - 005: new test anExplicitNullInAMergePatchLeavesTheFieldUnchanged (null = unchanged; only nulls = 400 empty-patch); walkthrough explains effectively-final and the AtomicBoolean holder. verify PASS 24 run.
  - 006: "what changed from cart-change-and-remove" note (PUT/PATCH/checkout dropped, lowercase SKUs normalised, POST returns CartView 200); reuses names the source stations.
  - 004: the two deliberate contract changes from 003 stated (unknown cart 404 not empty 200; merge over cap 409 not 400); Optional/orElseThrow walkthrough line; one-line Logger note. R16 caught a forward link in the walkthrough → reworded.
  - 002: lambdas and method references defined (using the controller's real lambda); testing strategy corrected (bug 3 uses MockMvc standalone); company links «fare-estimate-policies».
  - 008: reuses names 002/004; comparator section refocused on the generic method; size-cap trade-off replaced by "a new order shifts offsets between pages".
  - 001: hashCode added to the record's generated methods; advanced QA rewritten in plain language.
- Accepted, not changed: finding #9 (009 complexity) — the throttled eviction stays, because it fixes a real O(n)-per-request defect.
- Gates: validate --phase 1 PASS (10/10), test_validators PASS 16/16, export PASS for 001–010 and 067, render_check PASS 002, 008, 009.
- Tool note: piping render_site.sh into tail hung the shell until timeout (server already up); run render_check separately.

## 2026-10-10T12:55Z · S5 · station 011 shipment-status-transitions COMMITTED
- 21 files (13 main incl. 4 reused error/filter classes; 5 test). mvn verify PASS 50 run / 0 skipped on the first build. validate PASS (round 2: concepts 338 → >350 words, +1 basic QA for the 40% basic rule, two «slugs» that do not exist replaced with atomic-stock-decrement / kafka-first-events), export PASS, render PASS (concepts screenshot checked). Examples captured from the running jar.
- Verified: Jackson 3 wraps an unknown enum value as tools.jackson.databind.exc.InvalidFormatException (cause of HttpMessageNotReadableException) with getPath().getLast().getPropertyName() = "status"; EnumMap keys serialise in declaration order.
- Standard updated: ApiException.properties() adds extra problem members (currentStatus, allowedNext).
- Tool note: pkill -f with a pattern that also appears in the same shell command line kills the shell (exit 144) even with the [x] trick when the literal path is elsewhere in the command; stop jars in a separate call.

## 2026-10-10T13:40Z · S5 · station 012 store-service-layering COMMITTED
- 29 files (20 main incl. 6 reused error/filter classes; 5 test). Deep station, over the 8–15 guide because the lesson is the layer split itself (5 packages). mvn verify PASS 21 run / 0 skipped on the first build: 9 Mockito unit tests (strict stubs), 6 @WebMvcTest slice tests with @MockitoBean, 2 @SpringBootTest flow tests, 1 40-thread latch test, 3 bug reproductions (bug 3 deterministic via CyclicBarrier).
- validate PASS in round 3 (concepts 687 → 698 → >700 words; DELETE example captured from the jar and stored as response null, matching 005/006). export PASS, render PASS (design screenshot checked). Examples captured from the running jar.
- Design decisions: find-then-save made atomic with synchronized service methods (logged as a shortcut in code and prose); ApiException carrying a status kept and discussed openly as a trade-off; ProductCatalog/OrderHistory deliberately not behind interfaces.
- Tool note: render_site.sh under `timeout 60` printed "Terminated" this time, but the site was rebuilt and served (render_check PASS on station 12 data).

## 2026-10-10T14:30Z · S5 · station 013 promo-rules-wiring COMMITTED (+ validator rule R17)
- 25 files (16 main incl. 4 reused error/filter classes and the catalog; 6 test). mvn verify PASS 21 run / 0 skipped on the first build. validate PASS (round 2: concepts 297 → >350 words), export PASS, render PASS. Examples captured from the running jar; a real SIGTERM produced the @PreDestroy line "Promotion usage since start: {MILK-3FOR2=3, BREAKFAST-COMBO=2, FLAT50=1}".
- Verified: List<T> injection honours @Order on @Component classes and on @Bean methods from a @TestConfiguration; a single-bean injection with 2+ candidates fails as UnsatisfiedDependencyException caused by NoUniqueBeanDefinitionException; @Primary resolves it.
- Systemic defect found by the render check (bugs tab screenshot): the viewer prints users, bugs and qa as TEXT, so <code> and &quot; showed literally in every station's bugs (old data has the same wart). Per §6: new validator rule R17 (text-only fields hold no real HTML tags or entities; generics like <Object, Object> allowed), fixture added (test_validators PASS 17/17), authoring/plaintext.py applied in every authoring script before write. Regenerated all 14 stations: validate --all PASS, export PASS for all, render_check PASS on 004 and 013 (bugs tab now clean). Recorded in INTEGRATION_NOTES.md as an optional viewer change.
- First R17 draft flagged 067's "RedisTemplate<Object, Object>" as HTML; narrowed the rule to real tag names.

## 2026-10-10T12:45+05:30 · RESTART · user direction change
- User: build new real-world APIs, not the old-stations approach. Clarified: drop the old site format and every mapping to the old 100 stations; rebuild everything; new roadmap first, approved before building. Recorded in USER_DECISIONS.md (overrides LOOP_PROMPT.md where they conflict).
- Station 014 was not started (no files written). Loop stopped.
- Archived, not deleted: stations 001–013 + 067, site/, authoring/, old curriculum files, discovery.md, INTEGRATION_NOTES.md → archive/v1-2026-10-10/.
- Drafted curriculum/roadmap.json v2 (curriculum/build_roadmap.py): 100 standalone APIs, 30/30/40, every row its own business problem, concept-only prerequisites (all earlier). Waiting for approval.

## 2026-10-10T13:05+05:30 · S2 · roadmap v2.1
- User liked roadmap v2 ("yhi toh APIs hai realworld wali") and asked for 50 more high-value APIs. Added 50 (15 at 0-1, 15 at 0-2, 20 at 2-3), keeping 30/30/40 % → 45/45/60. Each new row inserted after the station whose concepts it needs; ids renumbered, prerequisites remapped by title and asserted earlier. Not yet approved for building.

## 2026-10-10T13:20+05:30 · S2 · roadmap v2.2
- User asked whether AWS is covered (only 2 direct stations were) and set the goal: job-ready for every real-world problem, all concepts clear, at most 200 stations. Added 49 (11 at 0-1, 17 at 0-2, 21 at 2-3): AWS set, Spring AOP/events, RabbitMQ, MongoDB, MySQL upserts, SOAP, LLM API, pgvector, security (SSRF, encryption at rest, vulnerable dependencies), on-the-job tasks (code review, dependency conflicts, Boot upgrade, bug triage), production depth (JVM/GC, WebFlux, PITR, multi-region DR, strangler fig, hexagonal, event sourcing, push at scale) and two capstones. 199 total; levels stay contiguous; prerequisites remapped and asserted earlier. Page and spreadsheet regenerated.

## 2026-10-10T13:50+05:30 · S2 · roadmap v2.4 (review applied)
- curriculum/enrich_roadmap.py adds stage, suggested_experience, track, trap (all 200, hand-written), station_types (word-boundary match + hand corrections after reading all 200), required_tests, reviewer_view, capstone milestones. build_roadmap.py: 088 concept fixed, tax/EMI/GST dated config, NEW3 station "API security audit (OWASP API Top 10)" → 200 total (56/63/81).
- First keyword pass for station types misfired (e.g. "stock-taking" → Concurrency, "ci" inside words → Operations); replaced with word-boundary regexes and 32 hand corrections.
- STATION_STANDARD.md written (18 README sections, required tests by type, honesty rules). Page and API_Backend_Engineering_Stations.xlsx regenerated; spreadsheet totals recalculated and checked against the JSON (200 / 187 core / 13 optional / 118 reviewer views).

## 2026-10-11T01:40+05:30 · S2 · industry gap research
- User asked whether the 200 stations reflect what 40 named companies (global + Indian) build today. Researched public engineering material and current platform releases (sources opened, listed in the doc). Wrote the findings as a Docs artifact "200 Stations vs Industry: Gap Research".
- Recommendation (not yet applied to roadmap.json): merge 13 overlapping stations, add 13 (MCP server, tool-calling agent with guardrails, AI gateway, CDC/Debezium, cell-based architecture, ReBAC sharing, card tokenisation, UPI AutoPay, Apache Camel, mutation/property/ArchUnit tests, COBOL-to-Java, ISO 20022, Account Aggregator), replace 079 TOTP with passkeys, update ~45 for Spring Boot 4 / Java 25 / Kafka 4 / LocalStack token / Valkey / OpenFeature / DPDP. Result 54/64/82.
- Corrections found in the roadmap: LocalStack free image now needs an account token (since 23 Mar 2026); virtual-thread pinning on synchronized fixed in JDK 24 (JEP 491).

## 2026-10-11T01:30+05:30 · S2 · roadmap v3.0 applied
- curriculum/round5.py (merges, renames, updates, NEW5) hooked into build_roadmap.py before numbering; prerequisites redirected from merged stations and kept only if earlier. enrich_roadmap.py: traps for 17 new/renamed stations, specialisations updated, 7 type corrections. Result 200 = 54/64/82; 14 new (13 added + passkeys), 189 core, 11 optional, 123 reviewer views.
- New renderers curriculum/render_page.py and curriculum/render_xlsx.py; page republished; API_Backend_Engineering_Stations_v3.xlsx built and recalculated (0 formula errors, totals match JSON). STATION_STANDARD.md baseline now Spring Boot 4 on Java 25.
- Note: the environment still has JDK 21 installed; building on Java 25 needs JDK 25 here (check at build start).

- 2026-10-10 Built sample station 085 (idempotent UPI-style payments) end to end on JDK 25 + Spring Boot 4.1.1 + Postgres 17 via Testcontainers: 21/21 tests pass; flawed review version fails 4; curl captures in docs/captures. Rendered tabbed sample page (curriculum/render_station_sample.py) and published it. Roadmap v3 still awaiting approval.
- 2026-10-10 Applied external review to station 085: Start-here beginner layer (story, analogy, key terms, 4-step flow, scope), why-lines on every API example, Practice tab with 2 tested challenges (24/24 with solutions) + 1 design task, README.md generated from the same content, demo-limit wording; STATION_STANDARD gains section 0 and 19.
- 2026-10-10 Applied second review to station 085: Locale.ROOT bug fixed (test proved it failed before), note rule, named DB constraints (range, parties, complete result) with bypass tests, 500 retry rule, IETF draft marked expired, GET auth boundary, partitioning qualified + challenge 4, Maven wrapper, JDK 21 path verified, try-it commands verified (1 row), tabs grouped in 3 levels, counts read from saved runs (31/31; flawed 26/31; challenges 34/34).
- 2026-10-11 Third review on 085: replay defined exactly (status, body, Location; only Idempotent-Replayed differs), retry-rules table (5xx/400/422/201/after retention), simulation wording (records, not money), retention limit at Understand and Go-deeper levels, starter and solutions packs split. 31/31 re-run.
- 2026-10-11 Handoff kit for Claude Code: generic renderer (085 page byte-identical), tools/build_station.sh (tests, flawed, challenges, captures, render, zips; 085 end to end in ~2 min), tools/check_station.py gate (085 OK; broken copy caught 7 problems), CLAUDE.md, LOOP_PROMPT.md, CONTEXT.md, INTEGRATION.md. Old loop prompt archived. STATE: built [85], next 1.

## 2026-10-13 · Claude Code (cloud) · batch 1 starts
- Owner asked for work in batches of 10 stations, with a zip of each finished batch for the Claude Design site. Batches go by id (001-010, 011-020, ...); 085 falls in batch 9.
- Environment: Docker daemon started by hand; Temurin JDK 25.0.1 installed in /opt/jdk25 from GitHub (api.adoptium.net is blocked by the proxy). 085 rebuilt: 31/31, gate OK.
- tools/build_station.sh: `docker compose down` ran even without compose.yaml and stopped stations with no infra under `set -e`; now runs only when compose was started.
- curriculum/station_render.py: shared helpers `pretty`, `capture`, `examples`, `challenge` for page.py files (085's page is byte-identical after the change). capture.sh writes curl args single-quoted so `capture()` can rebuild the request.
- Station 001 Is the dark store open?: 8/8 tests, challenges 14/14, no review view. A station test said lower-case ids are 400 while challenge 1 makes them 200; removed it from the station tests (the challenge now covers that case). Self-review: Understand tab explains closed (200) vs unknown (404) without code: yes. Claims match captures: yes. Simulation stated in header: yes. Each edge case points at a test: yes. Commands match files: yes. Phone width: 11 tabs, no overflow, no script errors.
- Station 002 Restaurant menu filters: 16/16 tests, challenges 22/22, no review view. Mutation: limit above sorted -> 4 tests red. Self-review: yes on all 7 (captures match page text; phone width 11 tabs, no overflow).
- Station 003 Product search autocomplete: 19/19 tests, challenges 26/26, no review view. Trap test counts work on 2 lakh generated products (200,026 names vs 5 entries). Mutation: index every position -> 2 red. Challenge test for out-of-stock first passed for the wrong reason (limit 2 never reached the hidden product); changed to limit 3. Self-review: yes on all 7.
- Station 004 Event registration form: 20/20 tests, challenges 26/26, no review view. Real bug found by a test: Jackson accepted tickets 2.5 as 2; fixed with spring.jackson.deserialization.accept-float-as-int=false (red before, green after). Mutation: no @Valid -> 4 red. Station tests now use a new email per test so challenge 1's duplicate rule cannot break them. Try-it commands with docs/*.json run by hand: 201 and 400 as the page says. Self-review: yes on all 7.
- Station 005 Designing REST resources for gym classes: 14/14 tests, challenges 21/21, no review view. Mutation: no capacity check -> 3 red. A cancellation-cutoff coding challenge was dropped: its tests would depend on today's date and fail after Oct 2026; it is a design task with a Clock hint instead. Self-review: yes on all 7.
- Station 006 One error shape for a banking API: 20/20 tests, flawed version 13/20 (7 failures, all 5 findings caught; each finding's named test checked against the failing list), challenges 26/26. Real finding: Spring's default type-mismatch problem echoed the path value; fixed (red before, green after). A security test compared a beneficiary's 404 with itself and could not fail; now compares with a truly unknown id, by problem fields so challenge 2's requestId does not break it. Renderer: capture() shows -u as an Authorization header (085 identical). Self-review: yes on all 7.
- Station 007 Comment moderation and XSS-safe output: 27/27 tests, flawed version 11/27 (16 failures, all 4 findings caught and checked by name), challenges 35/35. Two first-run failures were test mistakes (a '!' leet mapping turned 'IDIOT!' into 'idioti'; a '">' check matched the page's own markup), fixed in code and test. Encoded vs unencoded fragment opened in Chromium: encoded makes no <img> element; unencoded ran onerror. Self-review: yes on all 7.
- Station 008 Saved delivery addresses: 19/19 tests, challenges 27/27, no review view. Mutation: no Locale.ROOT on labels -> 1 red. Merge-patch error messages list allowed fields instead of echoing the sent field name. Self-review: yes on all 7 (captures show 405 Allow: PATCH, DELETE, PUT, GET and 204 on the repeated DELETE).
- Station 009 Wishlist without duplicates: 14/14 tests, challenges 19/19, no review view. Mutation: no upper-casing in Sku -> 7 red. The trap's 3-entry HashSet relies on identity hash codes differing (Object.hashCode); a collision is possible in theory but vanishingly unlikely. Self-review: yes on all 7.
- Station 010 Threaded comment replies: 13/13 tests, challenges 18/18, no review view. Mutation: recursive countBelow -> 2 red with StackOverflowError. Self-review: yes on all 7. Batch 1 (001-010) complete.
- Batch 1 review (ponytail-review) applied: 008 PATCH read-merge-write now one synchronized step (lost-update race); 010 countBelow keeps a seen set so a comment loop reached through rootId cannot spin forever (new test countingInsideALoopStops, red without the fix: timed out); 006/007 dropped accept-float-as-int config with no integer field to act on. 006, 007, 008, 010 rebuilt and gated: 20/20 (flawed 13/20), 27/27 (flawed 11/27), 19/19, 14/14.
- tools/pack_batch.sh added: packs batches/batch-NN-stations-AAA-BBB.zip only when all 10 stations pass the gate. Batch 1 packed: 10 stations, 171 tests, 1.2 MB.
- Station 011 Smart parking slot allocation: 15/15 tests, challenges 20/20, no review view. Mutation: floor division in Fee -> 4 red. Shared TestClock moved by other tests broke one test; now reset before each test. A station fee test (car 10 h = Rs 310) conflicted with the daily-cap challenge; changed to 7 h. Page number 65,160 corrected to 64,980 before render (computed). Self-review: yes on all 7.
- Station 012 Fleet vehicles: abstract classes vs interfaces: 8/8 tests, challenges 13/13, no review view. 404 had no body until spring.mvc.problemdetails.enabled (no advice class in this station). Mutation: body dropped from parts -> 4 red. A challenge test's expected order was wrong (worked out by hand and fixed before the solution run). Self-review: yes on all 7.
- Station 013 Recently viewed products with an LRU cache: 13/13 tests, flawed 7/13 (6 failures; all 3 findings caught), challenges 17/17. Lock removed entirely: concurrency test red 3/3 (ArrayIndexOutOfBounds inside LinkedHashMap). Only reads unlocked: green 5/5, so that flaw is described on the page as uncaught, not used in Review. Trap test runs two real app instances. Two-server try-it run by hand: 8081 [101], 8082 []. Self-review: yes on all 7.
- Station 014 Fare estimates per vehicle type: 12/12 tests, challenges 15/15, no review view. Mutation: meter floor removed -> 2 red. Contract tests changed to look fares up by vehicle name so challenge 1 (a new type) does not break them. Airport challenge numbers first used a wrong pickup (36.4 km); recomputed at 35.2 km and cross-checked in Python. Self-review: yes on all 7.
- Station 015 Splitting a group bill: 15/15 tests, challenges 19/19, no review view. A contract test's expected balance was my arithmetic slip (forgot one expense); recomputed term by term. Mutation: leftover paisa dropped -> 2 red. Captured settle-up balances sum to zero with 3 payments. Session worker restarted mid-station; work resumed from disk. Self-review: yes on all 7.
- Station 016 Loan EMI calculator and schedule: 12 tests (trap: same EMI every month ends at -1,191 paise; 4-decimal rounding quotes Rs 3 less). Testing 80 combinations found a small long loan going negative; schedule now closes early. Challenges: prepayment, disbursal date (18 with solutions).
- Station 017 GST on invoices: 11 tests (trap: hard-coded 18% IGST gives Rs 863.01; per-line rounding adds 2 paise over the CA's rate-wise 55,142). Dated slab rates via two floorEntry lookups. Challenges: line discounts, union territory UTGST (16 with solutions).
- Station 018 Payment methods with sealed interfaces: 11 tests (trap: nullable-field class refunds wallets to null and accepts UPI+card at once). Sealed PaymentMethod + records + exhaustive switches; real compile error captured; reflection test over permitted subclasses. Challenges: read back, PAY_LATER (15 with solutions).
- Station 019 A Money type for a multi-currency wallet: 13 tests (trap: one BigDecimal balance adds Rs 100 + USD 5 = 105; BigDecimal.equals splits 10.5/10.50). Money record of minor units + Currency; setScale without rounding refuses lost digits. Challenges: debits, indicative total (17 with solutions).
- Station 020 Bank statement pages: 12 tests (trap: unbounded size returns all 4,000 rows; int page x size overflows to a 500, real exception saved). Page<T extends Identified> with long offset; Comparator chain with id tie-breaker. Challenges: date range, largest first (16 with solutions).
- Batch 2 (stations 011-020) packed: batches/batch-02-stations-011-020.zip, 122 tests; starters for 016 and 020 re-zipped after page text fixes.
- Station 021 Parsing a bank statement CSV: 11 tests (trap: first bad line ends the file with no line number; SMART resolver turns 31/02 into 28 Feb). Per-line errors via checked LineException, strict dates. Renderer: --data-binary @file shows the file (085 byte-identical). Challenges: running balance, columns by name (15 with solutions).
- Station 022 Masking card and Aadhaar numbers in responses: 15 tests (trap: UI-only masking, full numbers in JSON and toString). Sensitive type with Jackson 3 ValueSerializer + masked toString; 401/403/not-yours 404; review: 4 flaws, 7 of 15 fail. Challenges: PAN, verify last 4 (18 with solutions).
- Station 023 Accepting a partner's snake_case JSON: 10 tests (trap: strict mapper throws on a new partner field; camelCase DTO reads nulls). Per-class @JsonNaming + ignoreUnknown, platform stays strict; zone-less IST times pinned. Jackson 3 defaults verified by a run. Challenges: duplicates, two time formats (13 with solutions).
- Station 024 Public holidays from a partner API: 10 tests (trap: no-timeout RestClient waits 2 s; provider 500 escapes as ours). @HttpExchange over RestClient with connect/read limits; 404/502/504 mapping, no partner text leaks; JDK HttpServer stub. Challenges: last good answer, API key (13 with solutions).
- Station 025 OTP request limiter: 14 tests (trap: check-send-record lets >3 of 20 through; per-server limit stated). compute() books atomically; CompletableFuture per Idempotency-Key covers simultaneous copies; Retry-After from oldest; injectable Clock. Review: 4 flaws, 7 of 14 fail. Challenges: key expiry, per-address limit (16 with solutions).
- Station 026 Request ids for parcel tracking: 14 tests (trap: MDC set but never cleared; next request on the thread logs the last id). OncePerRequestFilter with safe-id check and finally; requestId in problems; tracking.lookups metric; outage drill test + runbook. build_station.sh passes APP_LOG to capture.sh, so the page quotes the running app's real log lines. Challenges: access log, MDC on worker threads (16 with solutions).
- Station 027 Food order status flow: 11 tests (trap: status setter takes DELIVERED first and PICKED_UP after CANCELLED). Enum + EnumMap transition table, 409 with allowedNext, double tap no-op, atomic computeIfPresent (non-atomic version failed the race test 3/3 runs). Challenges: who may move (403), undo READY in 2 min (14 with solutions).
- Station 028 Library book loans in layers: 13 tests (trap: rules inline in web controller and a drifted kiosk copy). Controller/service/repository with constructor injection, repository interfaces, one advice for two controllers; Mockito service test and @WebMvcTest slice. Challenges: pay a fine, renew a loan (17 with solutions).
- Station 029 Travel insurance premium factors: 12 tests (trap: one-of-several injection fails, @Primary quick fix quotes 0, two orders give 183,875 vs 223,875). Ordered List<PremiumFactor>, @Qualifier vs @Primary rounding, @PostConstruct duplicate-order check, stateless singletons. Challenges: new factor bean, @ConditionalOnProperty campaign (14 with solutions).
- Station 030 Per-city delivery settings: 14 tests (trap: unvalidated primitives start with a typo and a Rs 0 minimum; client distance trusted). Validated @ConfigurationProperties records, ignoreUnknownFields=false, dev profile, env-var override, default DistanceCalculator as a real @AutoConfiguration, server-side haversine. Renderer: unknown file extensions shown as text (085 byte-identical). Challenges: free-delivery threshold, distance bands (18 with solutions).
- Batch 3 (stations 021-030) packed: batches/batch-03-stations-021-030.zip, 124 tests.
- Station 031 Appointment reminders in many languages: 12 tests. MessageSource bundles as whole sentences, Locale.lookup on Accept-Language, IndianRupees lakh grouping (JDK en-IN groups in threes), fallback-to-system-locale off with a test. Challenges: Marathi; choice-format 'when' counted in IST. build_station.sh now copies challenge/solution/*.properties into resources.
- Station 032 Return and refund eligibility: 38 tests (28 parameterized runs). Pure RefundRules + CsvSource/EnumSource table, Mockito stub-the-query/verify-the-command with strict stubs, fixed Clock in India. Trap: old shared switch case. Challenges: FOOTWEAR without breaking clothing; festive extension boundaries.
- Station 033 Bug triage from a customer ticket: 15 tests. Helpful NPE from a null coupon, real trace replayed by TicketReplay in capture.sh; fix at the cause (Coupon.NONE in Order's constructor); trap shows the entry-point patch missing the whole-order path. UnexpectedErrorHandler logs inside the request with rid, 500 carries requestId; metric, runbook, failure drill. Challenges: / by zero on a free order; requestId on every problem.
