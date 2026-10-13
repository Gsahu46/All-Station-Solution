# Station Line: loop prompt (one iteration = one station)

> **How to start.** Unzip this kit into a folder **outside** your website project. Open Claude Code in that folder and run:
>
> `/loop Run one iteration of LOOP_PROMPT.md exactly as written.`
>
> No interval: the loop paces itself. Or run a single iteration with: `Run one iteration of LOOP_PROMPT.md exactly as written.`
> You can stop at any time; the next run continues from `STATE.json`. Before the first iteration, run the one-time
> setup in `INTEGRATION.md` so finished stations can reach your website.

## Settings (edit if you want)

```
ORDER          = roadmap      # build stations in roadmap order: 001, 002, ... skipping ones already built
STOP_AFTER     = 0            # stop the loop after this many stations in one session (0 = keep going)
INTEGRATE      = yes          # after each station, copy its exports into the website as INTEGRATION_MAP.md says
GIT_COMMIT     = yes          # one commit per station in this kit folder (not in the website project)
```

## What wins when rules collide

1. **Correctness**: the code compiles, the tests pass, every technical claim is true for the pinned versions.
2. **Honesty**: no invented results, URLs, statistics or company internals. "Not verified" beats a false "verified".
3. **The owner's decisions** in `USER_DECISIONS.md` and `CONTEXT.md`.
4. **Clarity**: simplify the words, never the concept.
5. **Consistency with station 085** (structure, tabs, tone, depth for its stage).

Write any trade-off you make in `LOG.md`.

## The iteration

### 1. Resume
Read `CLAUDE.md` (once per session), `STATE.json`, the last 20 lines of `LOG.md`, and `USER_DECISIONS.md`.
Disk is your memory, not this conversation: if `STATE.json` says a station is in progress, check its folder and
continue from what is actually there. Never redo a station that `check_station.py` already passes.

### 2. Pre-flight
`java -version` (25, or 21 with `JAVA_VERSION=21`), `docker info`, `pandoc --version`, `zip -v`. If Docker is down and the
next station needs containers, say so and stop; never build without running the tests.

### 3. Pick
The next station in roadmap order that is not in `STATE.json.built`. Read its row in `curriculum/roadmap.json`:
title, company, industry, scenario, endpoints, concepts, infra, trap, station_types, required_tests, reviewer_view,
stage, prerequisites. Read the rows of its prerequisites too: use only concepts they taught.
Folder: `stations/NNN-kebab-title/` (NNN = id with 3 digits). Java package: `com.<company lowercased>.<area>`.
**Capstones (198, 199, 200)** are built one milestone per iteration (M1 to M5), in one folder; the page grows with each milestone.

### 4. Plan (write `stations/NNN-slug/docs/PLAN.md`, 30 lines at most)
The business problem in one paragraph; the endpoints with status codes; the tables and constraints; the trap and the
test that will show it; the test classes you will write (one per required type: names must contain
Trap, Contract, Database, Security/Auth, Concurrency, Messaging, Replay/Idempotency, Operations/Drill as they apply);
what is simulated; the two practice challenges; for reviewer_view stations, the 3 to 5 flaws the review version will have.

### 5. Build the project
Copy the skeleton from station 085 (`pom.xml`, `mvnw`, `mvnw.cmd`, `.mvn/`, `compose.yaml`, test base classes), then
change names, packages and dependencies. Keep only the starters this station uses. Then:
1. **Trap test first.** It reproduces the plausible-but-wrong behaviour against a naive version kept in the test sources
   (as `RetryWithoutKeyTrapTest` does), then shows the fixed API behaving.
2. Write the code, smallest version that meets the spec. Business rules also as named database constraints.
3. Write every required test against real infrastructure (Testcontainers). Real parallel requests for Concurrency.
   Duplicate delivery, retry and dead-letter tests for Messaging. Replay tests for Idempotency. 401, 403, cross-user
   access and malicious input for Security. Rollback and constraint-bypass tests for Database.
4. When you fix a bug, revert the fix once and confirm a test goes red. Note it in LOG.md.
5. `docs/capture.sh`: curl the running app for every case shown on the API tab (or run the CLI, for stations without
   an HTTP API), writing `docs/captures/NN-name.txt` and `date.txt`. Copy the pattern from 085.
6. `review/*.java` (reviewer_view stations only): a version a reviewer could approve that has real flaws. Each flaw must
   be caught by at least one of the station's tests.
7. `challenge/`: two coding challenges, each a ready test, plus `challenge/solution/*.java` and, if needed,
   `challenge/solution/pom-additions.xml`. Plus one or two design-on-paper tasks on the page.

### 6. Write the page: `stations/NNN-slug/docs/page.py`
Start from 085's `docs/page.py`. Same `META` keys, same 11 tabs in 3 levels, same helpers. Rewrite every word for this
station. Depth follows the stage:
- **Foundations**: short. Understand + Spec + API + Edge cases + Code + Tests + Practice carry the weight; Design,
  Production and Interview stay brief; Review only if reviewer_view.
- **Working Systems**: like 085.
- **Production Scale**: the Production tab adds the metric that shows the problem, the alert, how to roll back, a short
  runbook and a controlled failure drill (STATION_STANDARD §14). check_station.py looks for "runbook" and "failure drill".
Take numbers from saved runs (`N_TESTS`, `run("review-run.txt")`, `run("challenge-run.txt")`), never type them.
Follow the wording rules in STATION_STANDARD.md (exact meaning of replays, guarantees with limits, simulations, demo rules).

### 7. Build and gate
```bash
tools/build_station.sh stations/NNN-slug --capture
python3 tools/check_station.py stations/NNN-slug
```
Fix the root cause of anything that fails, then run both again. Up to 3 rounds. If it still fails, record the station
in `STATE.json.blocked` with the exact error, write it in LOG.md, and move on to the next station.

### 8. Self-review (answer each in LOG.md with yes or the fix you made)
- Could a beginner explain the problem after the Understand tab alone, without code?
- Does every claim on the page match the code and a saved run?
- Is anything simulated described as real? Any guarantee stated without its limit?
- Does every edge case point to a test that exists?
- Does the flawed version fail for the reasons the findings give?
- Do the Windows and macOS/Linux commands match the files in the project?
- Open `exports/NNN-slug/page.html` in a browser once (or screenshot it): tabs switch, code is readable, no layout break at phone width.

### 9. Integrate (if INTEGRATE = yes)
Do exactly what `INTEGRATION_MAP.md` says for one station: copy its exports into the website project and update the
station list there. Change nothing else in the website. If the map is missing, skip this step and say so in the report.

### 10. Commit
Update `exports/index.json` (the build script does it). Append to `LOG.md`: station, tests passed/total, flawed-version
result, challenge result, time taken, anything skipped and why. Update `STATE.json` last: add the id to `built`, set
`next_station`, clear `in_progress`. If GIT_COMMIT = yes: `git add -A && git commit -m "Station NNN: <title>"` in this folder.

### 11. Report (5 lines at most) and continue
Station built, test result, anything skipped or blocked, what is next. Never paste file contents. Stop the loop when all
200 are built, when STOP_AFTER is reached, when Docker or the JDK is missing, or when the owner must decide something.
