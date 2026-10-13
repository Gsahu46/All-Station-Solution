# Station standard (applies to every one of the 200 stations)

Each station is a standalone Spring Boot 4 project on Java 25 (LTS). Its README.md has these sections, in this order.
The depth scales with the station: a Foundations station is short; a capstone is long.
The README and the station page are generated from the same content (each station's docs/page.py, rendered by curriculum/station_render.py through tools/build_station.sh), so they never disagree.

Every station is read in three levels, shown as grouped tabs on the page:
**1 Understand** (about 5 minutes, no code) → **2 Build** (spec, API, edge cases and trap, set-up and code, tests, practice)
→ **3 Go deeper** (design, production, interview, review). A beginner can stop after level 1 and still understand the problem.
Any simulation (no real bank, no real network) is stated in the page header, not only further down.

0. **Understand** (no code) — the real-life problem as a 3-step story; what we are building in two sentences; an everyday
   analogy; how it works in 4–5 steps; one check-yourself question with a hidden answer; what the station is not
   (simulations, missing auth, demo-only limits); key terms, each with a simple meaning, an everyday example and its use here.
0b. **Set up and run** — required versions (JDK, Docker), Maven wrapper commands for Windows and macOS/Linux, try-it commands
   with expected results (including a database row count), and a troubleshooting table. Every command is run before shipping.
   Code walkthrough lists files in the order a request travels; each main class says what it does, why it exists, what breaks without it.
1. **Business problem** — the fictional company, what breaks today, who it hurts. Companies are fictional, inspired by real industries.
2. **Acceptance criteria** — Given / When / Then statements that define "done".
3. **Requirements** — what the API must do, as rules.
4. **Learning objectives** — what the learner will be able to do and explain.
5. **API contract** — methods, URLs, request and response bodies, headers, status codes, error bodies, and real request/response examples captured from the running app, each with one line on why the API answered that way.
6. **Edge cases and failure cases** — invalid input, missing resources, duplicates, unauthorised access, timeouts, races, unavailable dependencies: whichever apply.
7. **The trap** — the plausible-but-wrong approach (from the roadmap's `trap` field), shown failing, with a test where code can show it.
8. **Implementation approach** — numbered steps before any code.
9. **Design alternatives and trade-offs** — what else was possible, and what each choice costs.
10. **Complete working code** — readable, no hidden steps.
11. **Code explanation** — the important lines and decisions, in plain language.
12. **Database design** — entities, relationships, constraints, indexes, migrations, transaction boundaries (when there is a database).
13. **Testing** — the required tests (below), each named, with what it proves. The first test written reproduces the failure before the fix.
14. **Operations** (Production Scale stations) — the metric that shows the problem, the alert that should fire, how to roll back, a short runbook, and a controlled failure drill.
15. **Real-world considerations** — security, performance, reliability, scale, cost, maintainability.
16. **Interview takeaways** — questions a learner should answer out loud, with strong answers.
17. **Self-check rubric** — correctness, robustness, design, tests, explanation.
18. **Reviewer view** (stations marked `reviewer_view`) — a flawed version in `review/` to find and fix, with the reasoning.
    The flawed version is run against the station's tests and the real failures are shown.
19. **Practice challenges** — two coding challenges, each with a ready test in `challenge/` and a solution in
    `challenge/solution/`, plus one design-on-paper task. Every challenge test is run against its solution before the station ships.
    Learners download two packs: the starter project (no solutions) and a separate solutions pack. On the page a solution
    opens only on click.

Wording rules that apply to every station: say exactly what a replay or "same response" includes and what differs; state
any guarantee together with its limit (for example, idempotency holds only while the key is retained); and in a simulation,
talk about records being created, never about money moving.

## Required tests by station type

Every station: HTTP contract tests (valid, invalid, not found) and a test that reproduces the failure before the fix.
Then, by the roadmap's `station_types`:

| Type | Required tests |
|---|---|
| Database | rollback and constraint tests against a real database |
| Security | 401, 403, one user accessing another user's data, malicious input |
| Concurrency | a real concurrency test that proves the invariant holds |
| Messaging | duplicate-delivery, retry and dead-letter tests |
| Idempotency | a replay test: the same request twice gives one effect |
| Operations | operations section plus a controlled failure drill |

These are checked by tools/check_station.py: a station of a type cannot pass without a test class named for it
(Trap, Contract, Database, Security or Auth, Concurrency, Messaging, Replay or Idempotency, Operations or Drill).

## Honesty rules

- Tests that need Docker, LocalStack or real AWS are marked as skipped in this build environment, never reported as passed.
- "Challenge tests" for learners live in `challenge/`; there are no hidden tests in a downloadable project.
- Financial rules (EMI, GST, income tax) are learning exercises with rates in dated configuration, not tax or financial advice.
- Limits and amounts used for validation (for example a ₹1,00,000 maximum) are called demo rules, never presented as official limits.
- Business rules validated in Java are also enforced as named database constraints, with a test that bypasses Java.
- Standards are cited with their status: an expired or unpublished draft is never presented as a standard.
- Every test count on the page is read from a saved run in `docs/` (station, flawed version, challenges), never typed by hand.
- Identifiers are normalised with `Locale.ROOT`; a server's locale must never change behaviour.
- The platform builds skills, judgement and a portfolio for backend roles; it does not claim to equal years of production experience.
