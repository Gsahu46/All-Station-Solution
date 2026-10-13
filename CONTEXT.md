# Context: how this project got here (11 Oct 2026)

Written at the end of a long claude.ai session so Claude Code can continue without it. The owner writes in Hinglish;
reply in the same mix when you talk to them, and keep code, pages and READMEs in English.

## The goal (VISION.md)

A learning platform of real-world Java Spring Boot backend API "stations" for developers with 0 to 3 years of
experience. Finishing them should make a person ready for real IT work: every concept clear, every station tested and
industry-relevant. Hard cap: **200 stations, never more**. Levels were meant to split about 30/30/40 across 0-1, 0-2 and
2-3 years of experience.

## Decisions the owner made (do not reopen)

| When (IST) | Decision |
|---|---|
| 10 Oct, 12:18 | Throw away the old 100 stations and their site format. Build new, standalone, real-world APIs. No mapping to old stations. Show the roadmap before building. |
| 10 Oct, 12:52 | Liked the new real-world list; add 50 more high-value APIs (150). |
| 10 Oct, 13:09 | No fixed count, but never more than 200; the learner must be job-ready; AWS included. |
| 10 Oct, 13:36 | Applied an external review: a trap per station, a security audit station, payment failover fix, stage names, Core vs Specialisation, station types with required tests, reviewer view, staged capstones. |
| 11 Oct, 01:03 | Applied deep industry research (20 global + 20 Indian companies): roadmap v3.0. 13 merges, 13 new stations (MCP server, Zanzibar-style sharing, card tokens, UPI AutoPay, Camel, CDC, AI gateway, tool-calling agent, cell architecture, COBOL to Java, ISO 20022, Account Aggregator, weak-test detection), passkeys instead of TOTP, Java 25 + Spring Boot 4 baseline. |
| 11 Oct, 01:33 | Asked for one sample API solved completely, to see what tabs a station needs: station 085. |
| 11 Oct, 02:01 to 12:18 | Sent three external reviews of station 085; all applied (see below). The third review was sent twice; the second copy needed no changes. |
| 11 Oct, 12:39 | Asked for this loop prompt and context, to build all 200 with Claude Code and integrate them into the website (designed in Claude Design). Taken as approval of roadmap v3 and of station 085 as the format. |

## The roadmap (curriculum/roadmap.json, v3.0)

- 200 stations: Foundations 54, Working Systems 64, Production Scale 82. Core 189, Specialisation 11.
- 123 stations have a reviewer view (a flawed version to review). Capstones 198, 199, 200 have five milestones each.
- Infra: 80 PostgreSQL, 65 none, then Redis/Valkey, Kafka, multi-service, LocalStack (AWS), RabbitMQ, MongoDB, OpenSearch, Kubernetes, Terraform, CI.
- India-specific stations: UPI-style payments and AutoPay mandates, RBI card tokenisation, Account Aggregator, GST, DPDP Rules 2025.
- Known, accepted gaps (told to the owner): no DSA/LeetCode practice, no system-design interview format, no behavioural
  rounds, no Git/Linux basics; Foundations is 27%, below the 30% target. The stations build job skill, not interview drill.
- Published pages in the owner's claude.ai account: the 200-station roadmap page ("API & Backend Engineering Stations"),
  the research doc ("200 Stations vs Industry: Gap Research"), and the station 085 sample page.

## Station 085: the reference (stations/085-idempotent-upi-payments)

Idempotent UPI-style payments for a fictional app, Paysetu. `POST /payments` with an `Idempotency-Key`, `GET /payments/{id}`.
Spring Boot 4.1.1, Java 25, PostgreSQL 17, JdbcClient, Flyway, Testcontainers. 31 tests, all passing on JDK 25 and 21.

How it was shaped, in order:
1. First build: 21 tests. The contract tests caught a real bug in my own error handler (body validation errors arrive as
   `HandlerMethodValidationException` once a header has a constraint). A flawed "check-then-insert" version, run under
   20 parallel retries, charged one customer between 2 and 19 times in 5 runs; it still passed the simple retry test.
2. Review 1 (beginner focus): added the plain-language Understand layer (story, analogy, key terms, 4-step flow,
   scope), a "why" line on every example, a Practice tab with two tested challenges and a design task, README generated
   from the same content.
3. Review 2 (correctness): fixed a real locale bug (`toLowerCase()` under a Turkish locale broke retries; a test now
   proves it), defined "missing note = empty note", added named database constraints with bypass tests, the precise 500
   retry rule, the IETF draft marked as expired, the auth boundary for `GET /payments/{id}`, a corrected partitioning
   claim, the Maven wrapper, Windows commands, troubleshooting, a verified try-it run, and three levels:
   Understand, Build, Go deeper.
4. Review 3 (wording): exact meaning of "the same response" (status, body and Location; only `Idempotent-Replayed`
   differs), a retry-rules table, "a record was created" instead of "money moved", the retention limit stated at both
   levels, and solutions shipped separately from the starter project.

All of these became rules in STATION_STANDARD.md, so the other 199 stations start where 085 ended.

## What the owner sees and approves

- A station page with 11 tabs in 3 levels. 085's page also shows a "page blueprint" table; other stations hide it.
- Downloads: a starter project and a separate solutions pack.
- The owner forwards stations to an outside reviewer; expect more review rounds. Apply what is correct, push back with
  evidence (a test, a run) where a review is wrong, and turn every accepted point into a rule in STATION_STANDARD.md.

## Environment facts from the session

- Docker can be down after a restart: start it before building. Testcontainers needs it.
- JDK 25 had to be installed (Temurin from GitHub); the system JDK was 21.
- `pkill -f <pattern>` can kill its own shell when the pattern is on the command line; use the `[x]` trick.
- Escaping in generated Python strings went wrong once; after a scripted edit, re-render and compare.
