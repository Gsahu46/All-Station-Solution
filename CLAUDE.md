# Station Line: 200 real-world Spring Boot API stations

You are building a learning platform: 200 standalone Spring Boot API projects ("stations") that take a developer
from 0 to 3 years of experience. Each station is a real business problem with working code, real tests and teaching
material in three levels. The roadmap is final; your job is to build the stations, one per iteration, to the standard
that station 085 sets, and export each one so the owner's website can show it.

Read these before your first iteration, in this order:
1. `CONTEXT.md`: how the project got here and every decision the owner made (do not reopen them).
2. `STATION_STANDARD.md`: what every station must contain. It is the contract.
3. `stations/085-idempotent-upi-payments/`: the reference station. Copy its shape, not its content.
4. `LOOP_PROMPT.md`: what one iteration does.
5. `INTEGRATION.md`: how built stations reach the owner's website.

## Folder map

```
CLAUDE.md, CONTEXT.md, LOOP_PROMPT.md, INTEGRATION.md   handoff documents
STATION_STANDARD.md      the contract for every station
VISION.md                the owner's original brief
USER_DECISIONS.md        decisions that override anything else, newest last
STATE.json               progress: built stations, next station, blockers (update last, it is the commit marker)
LOG.md                   append-only, one entry per iteration
curriculum/roadmap.json  the 200 stations: title, scenario, endpoints, concepts, trap, types, required tests, prerequisites
curriculum/station_render.py + station_page_template.html   renders a station's page, README and station.json
curriculum/roadmap-source/   scripts that produced roadmap.json (history; do not edit the roadmap without the owner)
tools/build_station.sh   one command: tests, flawed version, challenges, captures, render, zips
tools/check_station.py   the gate: a station is done only when this prints OK
stations/NNN-slug/       one Maven project per station
exports/NNN-slug/        what the website consumes: page.html, station.json, starter.zip, solutions.zip
exports/index.json       list of built stations
```

## Non-negotiables

- **Never invent results.** Every test count, example response and "it works" comes from a real run saved in `docs/`.
  If something cannot run here (no Docker, no LocalStack token, no LLM key), the test is skipped with a reason in
  `docs/SKIPPED.md` and the page says so. Never report a skipped test as passed.
- **One station per iteration**, fully done (check_station.py OK), then stop. Do not half-build several.
- **Standalone stations.** A station never imports or extends another station's code. Prerequisites are concepts only.
- **Do not change the roadmap** (titles, order, count, types). If a station looks wrong, note it in STATE.json
  `blocked` with the reason and ask the owner. Build the next one meanwhile.
- **Simulations say so.** Payments, banks, UPI, courier, SMS and AI providers are simulated unless the station is about
  integrating them. Say "a record is created", never "money moved". State it in `META["simulation"]`.
- **Guarantees come with their limits** (for example "safe while the key is retained"). Demo limits are "demo rules".
  Cite standards with their status (an expired IETF draft is not a standard).
- **Business rules in Java are also database constraints**, named, with a test that bypasses Java.
- **Identifiers are normalised with `Locale.ROOT`.** Money is integer minor units (paise), never double.
- **Do not touch the owner's website project** except through the steps in INTEGRATION.md.

## Stack (pinned; verified while building 085)

- Java 25 (Temurin 25.0.1). Java 21 also works with `-Djava.version=21` (verified: 31/31 on 085).
- Spring Boot 4.1.1, Spring Framework 7, Jackson 3, JUnit 6, Testcontainers 2.0.x, PostgreSQL 17, Maven wrapper 3.9.11.
- Starters are split: `spring-boot-starter-webmvc`, `spring-boot-starter-jdbc`, `spring-boot-starter-flyway`
  (+ `org.flywaydb:flyway-database-postgresql`), test: `spring-boot-resttestclient`, `spring-boot-testcontainers`,
  `org.testcontainers:testcontainers-postgresql` (class `org.testcontainers.postgresql.PostgreSQLContainer`).
- `RestTestClient`: `org.springframework.test.web.servlet.client.RestTestClient`, enabled by
  `@AutoConfigureRestTestClient` (`org.springframework.boot.resttestclient.autoconfigure`).
- Jackson 3 lives in `tools.jackson.*` (`tools.jackson.databind.json.JsonMapper`); annotations stay in `com.fasterxml.jackson.annotation`.
  `FAIL_ON_NULL_FOR_PRIMITIVES` is on: a missing `int` in a body is a 400.
- `@MockitoSpyBean` / `@MockitoBean`: `org.springframework.test.context.bean.override.mockito`.
- A constraint annotation on a controller parameter (e.g. `@Pattern` on a header) switches on method validation:
  `@Valid` body errors then arrive as `HandlerMethodValidationException`, not `MethodArgumentNotValidException`.
- `HttpStatus.UNPROCESSABLE_CONTENT` (422). Errors are RFC 9457 `ProblemDetail`; `ErrorResponseException` needs no handler.
- No trailing-slash matching: `/payments/` is a 404.
- `compose.yaml` services need a `healthcheck`, so `docker compose up --wait` means ready.
- LocalStack images need `LOCALSTACK_AUTH_TOKEN` (since 23 Mar 2026). Redis 8 is AGPL; use Valkey for Redis stations.
  Kafka 4 runs in KRaft mode (no ZooKeeper). Prefer `RestClient` / HTTP service clients; `RestTemplate` is deprecated in Spring 7.1.

## Commands

```bash
tools/build_station.sh stations/NNN-slug --capture   # full build (about 2 minutes for 085)
python3 tools/check_station.py stations/NNN-slug      # the gate
python3 curriculum/station_render.py stations/NNN-slug exports/NNN-slug   # re-render only
```
Needs JDK 25 on PATH (or `JAVA_VERSION=21`), Docker running, python3, pandoc, zip, curl.

## Lessons already paid for

- Docker can stop between sessions; "Could not find a valid Docker environment" means start Docker, not a code bug.
- A test that cannot fail proves nothing: when you fix a bug, revert the fix once and watch the test go red.
- The flawed `review/` version must fail real tests; record which in the Review tab (numbers come from docs/review-run.txt).
- Concurrency needs a real parallel test (virtual threads + a start latch); a single-threaded "send twice" test passed on a version that charged 19 times.
- Keep page numbers out of prose: read them from saved runs (`N_TESTS`, `run(...)`) so they never go stale.
