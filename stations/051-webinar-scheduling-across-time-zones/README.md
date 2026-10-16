# Station 051 · Webinar scheduling across time zones

Foundations · 0–1 years · Core · SaaS · Types: none

Spring Boot 4.1.1 · Java 25 · java.time (Instant, LocalDateTime, ZonedDateTime, ZoneRules, TemporalAdjusters) · Clock with @TestBean · RFC 9457 problem details. Needs JDK 25 (or 21, see Set up & code). No Docker, no database. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Webinars are demo records kept in memory: no video room, invitation or reminder is created, and they are gone when the app restarts. Time zone rules are the ones shipped with the JDK that ran the captures.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 10 tests.

# 1 · Understand

## The problem in real life

1.  **10:00 for everyone**

    Taskloom's host in Bengaluru set a webinar for 10:00. Attendees in London saw 10:00 too, and joined five and a half hours late.

2.  **Then an hour off**

    A fix stored the moment in UTC, but repeated series by adding a month in UTC. When the US left daylight saving, a New York host's 10:00 sessions moved to 09:00.

3.  **The fix**

    Turn the host's wall-clock time into a moment using the host's zone, separately for every session; store the moment; show it in each viewer's zone.

A clock time without a place is not a moment. Store the moment; show it in each person's own clock.

## What are we building?

A host creates a webinar at their own wall-clock time and zone (`POST /webinars`), optionally repeating monthly. Anyone reads it in their zone (`GET /webinars/{id}?viewerZone=…`), and every session shows the moment in UTC, the host's time and the viewer's time, each with its offset.

## An everyday analogy

A train timetable says 10:00 because everyone reading it is at that station. A video call has no single station: you send "10:00 in Bengaluru", and each person's phone turns it into their own time. The phone needs the place, not just "10:00".

## How it works in 4 steps

1.  **The host sends** 10:00, 5 Nov, Asia/Kolkata.
2.  **The server asks the zone's rules** which offset that wall time has on that date (+05:30), refusing a time that is skipped or repeated.
3.  **It stores** the moment, 04:30 UTC, with the host's zone.
4.  **Each viewer** sees that moment in their own zone: 04:30 in London, 20:30 the evening before in Los Angeles.

Check yourself: a monthly New York webinar at 10:00. Why does it move from 19:30 to 20:30 in India in November?

New York leaves daylight saving on 1 November (−04:00 becomes −05:00); India has no daylight saving. The host's 10:00 stays 10:00, so the moment moves one hour later, and India sees it an hour later. That is correct. The old code kept the moment fixed and moved the host.

## What this station is not

- **No reminders or invitations.** Times only.
- **No weekly series.** Challenge 1.
- **No database.** Webinars live in memory.

## Key terms

| Term                              | Simple meaning                                                   | Everyday example                                    | In this project             |
|-----------------------------------|------------------------------------------------------------------|-----------------------------------------------------|-----------------------------|
| **Instant**                       | One moment on the world's timeline, the same everywhere.         | The moment a cricket match's first ball is bowled.  | `startsAt` (UTC)            |
| **LocalDateTime**                 | A date and a clock time, with no place: it is not a moment.      | "10:00 on 5 Nov" written on a sticky note.          | What the host types         |
| **Time zone**                     | A region's rules for its clocks, including daylight saving.      | Asia/Kolkata, Europe/London.                        | `zone`, `viewerZone`        |
| **Offset**                        | How far a clock is from UTC at one moment.                       | India is always +05:30; London is +00:00 or +01:00. | `+05:30` in each time shown |
| **Daylight saving gap / overlap** | An hour that does not exist, or happens twice, when clocks jump. | 02:30 on the night US clocks spring forward.        | `422` answers               |
| **Clock**                         | Where the program asks "what time is it now?".                   | The office wall clock everyone checks.              | A fixed Clock in tests      |

# 2 · Build: Spec

## Business problem

**Taskloom** (a fictional SaaS for project teams) runs webinars for customers in many countries. Times were shown wrongly abroad and drifted when daylight saving changed.

## Acceptance criteria

1.  **Given** 10:00 on 5 Nov 2026 in Asia/Kolkata, **then** London sees 04:30 and Los Angeles 20:30 on 4 Nov.
2.  **Given** a monthly 10:00 series in New York from 20 Oct, **then** the host sees 10:00 both months, and India sees 19:30, then 20:30.
3.  **Given** monthly from 31 Jan 2027, **then** 28 Feb, 31 Mar, 30 Apr; from 31 Jan 2028, 29 Feb.
4.  **Given** a time the clocks skip (02:30, 14 Mar 2027, New York), **then** `422`; a time that happens twice (01:30, 1 Nov 2026), `422` unless the offset is named.
5.  **Given** a first session that has already started by the server's clock, **then** `422`.
6.  **Given** `IST` or `+05:30` as a zone, a malformed date, or 10 minutes, **then** `400`; an unknown webinar, `404`.

## Requirements

- Store moments (`Instant`) and the host's zone; never a bare `LocalDateTime`.
- Each session of a series is resolved on its own date in the host's zone.
- Zones are region ids (`Asia/Kolkata`), never abbreviations or fixed offsets.
- "Now" comes from an injected `Clock`.

## Learning objectives

- Tell `Instant`, `LocalDateTime`, `ZonedDateTime` and `OffsetDateTime` apart and pick the right one.
- Handle daylight saving gaps and overlaps on purpose.
- Do date arithmetic in the right zone, and with month ends and leap years.
- Test time-dependent code with a fixed `Clock`.

# 2 · Build: API contract

## Endpoints

| Method | Path                                      | Purpose                                                                                                                                                                                                                                          |
|--------|-------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `POST` | `/webinars`                               | Create: `title`, `startsAt` (host's wall-clock time, no offset), `zone`, `durationMinutes` (15 to 480), optional `repeat` (`NONE`, `MONTHLY`, `MONTHLY_LAST_WEEKDAY`) and `sessions` (1 to 12), optional `offset` for a time that happens twice. |
| `GET`  | `/webinars/{id}?viewerZone=Europe/London` | Every session as `startsAt` (UTC), `hostTime` and `viewerTime`. Without `viewerZone`, the host's zone.                                                                                                                                           |

## Status codes

| Status | When                                                                                                |
|--------|-----------------------------------------------------------------------------------------------------|
| 201    | Created; `Location` points at it                                                                    |
| 200    | The webinar, in the viewer's zone                                                                   |
| 400    | Malformed body, an unknown zone (including `IST` and `+05:30`), duration or sessions out of range   |
| 404    | No such webinar                                                                                     |
| 422    | Already started; a time skipped or repeated by daylight saving; a series that does not fit its rule |

## Captured examples

Captured with curl from the running app on 16 Oct 2026, in this order. JSON bodies are indented for reading; `Date` and connection headers are left out.

### Case 1: 10:00 on 5 Nov in Asia/Kolkata

**Why:** stored as 04:30 UTC; shown to the host as 10:00+05:30.

Request

``` code
POST /webinars HTTP/1.1
Content-Type: application/json

{
  "title": "Planning your first sprint",
  "startsAt": "2026-11-05T10:00",
  "zone": "Asia/Kolkata",
  "durationMinutes": 60
}
```

Response

``` code
HTTP/1.1 201 
Location: /webinars/1
Content-Type: application/json

{
  "id": 1,
  "title": "Planning your first sprint",
  "hostZone": "Asia/Kolkata",
  "viewerZone": "Asia/Kolkata",
  "durationMinutes": 60,
  "sessions": [
    {
      "startsAt": "2026-11-05T04:30:00Z",
      "hostTime": "2026-11-05T10:00:00+05:30",
      "viewerTime": "2026-11-05T10:00:00+05:30"
    }
  ]
}
```

### Case 2: seen from London

**Why:** 04:30 (London is on +00:00 in November). The old app said 10:00.

Request

``` code
GET /webinars/1?viewerZone=Europe/London HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 245

{
  "id": 1,
  "title": "Planning your first sprint",
  "hostZone": "Asia/Kolkata",
  "viewerZone": "Europe/London",
  "durationMinutes": 60,
  "sessions": [
    {
      "startsAt": "2026-11-05T04:30:00Z",
      "hostTime": "2026-11-05T10:00:00+05:30",
      "viewerTime": "2026-11-05T04:30:00Z"
    }
  ]
}
```

### Case 3: seen from Los Angeles

**Why:** 20:30 on 4 November, the evening before.

Request

``` code
GET /webinars/1?viewerZone=America/Los_Angeles HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 256

{
  "id": 1,
  "title": "Planning your first sprint",
  "hostZone": "Asia/Kolkata",
  "viewerZone": "America/Los_Angeles",
  "durationMinutes": 60,
  "sessions": [
    {
      "startsAt": "2026-11-05T04:30:00Z",
      "hostTime": "2026-11-05T10:00:00+05:30",
      "viewerTime": "2026-11-04T20:30:00-08:00"
    }
  ]
}
```

### Case 4: monthly from 20 Oct, 10:00 New York

**Why:** 10:00 both months for the host; the offset changes from −04:00 to −05:00.

Request

``` code
POST /webinars HTTP/1.1
Content-Type: application/json

{
  "title": "Planning your first sprint",
  "startsAt": "2026-10-20T10:00",
  "zone": "America/New_York",
  "durationMinutes": 60,
  "repeat": "MONTHLY",
  "sessions": 2
}
```

Response

``` code
HTTP/1.1 201 
Location: /webinars/2
Content-Type: application/json

{
  "id": 2,
  "title": "Planning your first sprint",
  "hostZone": "America/New_York",
  "viewerZone": "America/New_York",
  "durationMinutes": 60,
  "sessions": [
    {
      "startsAt": "2026-10-20T14:00:00Z",
      "hostTime": "2026-10-20T10:00:00-04:00",
      "viewerTime": "2026-10-20T10:00:00-04:00"
    },
    {
      "startsAt": "2026-11-20T15:00:00Z",
      "hostTime": "2026-11-20T10:00:00-05:00",
      "viewerTime": "2026-11-20T10:00:00-05:00"
    }
  ]
}
```

### Case 5: the series seen from India

**Why:** 19:30, then 20:30: the moment moved, the host's 10:00 did not.

Request

``` code
GET /webinars/2?viewerZone=Asia/Kolkata HTTP/1.1
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 369

{
  "id": 2,
  "title": "Planning your first sprint",
  "hostZone": "America/New_York",
  "viewerZone": "Asia/Kolkata",
  "durationMinutes": 60,
  "sessions": [
    {
      "startsAt": "2026-10-20T14:00:00Z",
      "hostTime": "2026-10-20T10:00:00-04:00",
      "viewerTime": "2026-10-20T19:30:00+05:30"
    },
    {
      "startsAt": "2026-11-20T15:00:00Z",
      "hostTime": "2026-11-20T10:00:00-05:00",
      "viewerTime": "2026-11-20T20:30:00+05:30"
    }
  ]
}
```

### Case 6: monthly from 31 January

**Why:** each month's last day when the 31st does not exist, counted from the first date.

Request

``` code
POST /webinars HTTP/1.1
Content-Type: application/json

{
  "title": "Planning your first sprint",
  "startsAt": "2027-01-31T10:00",
  "zone": "Asia/Kolkata",
  "durationMinutes": 60,
  "repeat": "MONTHLY",
  "sessions": 4
}
```

Response

``` code
HTTP/1.1 201 
Location: /webinars/3
Content-Type: application/json

{
  "id": 3,
  "title": "Planning your first sprint",
  "hostZone": "Asia/Kolkata",
  "viewerZone": "Asia/Kolkata",
  "durationMinutes": 60,
  "sessions": [
    {
      "startsAt": "2027-01-31T04:30:00Z",
      "hostTime": "2027-01-31T10:00:00+05:30",
      "viewerTime": "2027-01-31T10:00:00+05:30"
    },
    {
      "startsAt": "2027-02-28T04:30:00Z",
      "hostTime": "2027-02-28T10:00:00+05:30",
      "viewerTime": "2027-02-28T10:00:00+05:30"
    },
    {
      "startsAt": "2027-03-31T04:30:00Z",
      "hostTime": "2027-03-31T10:00:00+05:30",
      "viewerTime": "2027-03-31T10:00:00+05:30"
    },
    {
      "startsAt": "2027-04-30T04:30:00Z",
      "hostTime": "2027-04-30T10:00:00+05:30",
      "viewerTime": "2027-04-30T10:00:00+05:30"
    }
  ]
}
```

### Case 7: 02:30 on 14 Mar 2027 in New York

**Why:** clocks jump from 02:00 to 03:00: `422`.

Request

``` code
POST /webinars HTTP/1.1
Content-Type: application/json

{
  "title": "Planning your first sprint",
  "startsAt": "2027-03-14T02:30",
  "zone": "America/New_York",
  "durationMinutes": 60
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "2027-03-14T02:30 does not exist in America/New_York: the clocks skip it for daylight saving.",
  "instance": "/webinars",
  "status": 422,
  "title": "Not a schedulable time"
}
```

### Case 8: 01:30 on 1 Nov 2026 in New York

**Why:** clocks go back, so 01:30 happens at −04:00 and −05:00: `422` until an offset is sent.

Request

``` code
POST /webinars HTTP/1.1
Content-Type: application/json

{
  "title": "Planning your first sprint",
  "startsAt": "2026-11-01T01:30",
  "zone": "America/New_York",
  "durationMinutes": 60
}
```

Response

``` code
HTTP/1.1 422 
Content-Type: application/problem+json

{
  "detail": "2026-11-01T01:30 happens twice in America/New_York (-04:00 and -05:00) as the clocks go back; send \"offset\" to choose.",
  "instance": "/webinars",
  "status": 422,
  "title": "Not a schedulable time"
}
```

### Case 9: zone "IST"

**Why:** IST means India, Ireland or Israel: `400`.

Request

``` code
POST /webinars HTTP/1.1
Content-Type: application/json

{
  "title": "Planning your first sprint",
  "startsAt": "2026-11-05T10:00",
  "zone": "IST",
  "durationMinutes": 60
}
```

Response

``` code
HTTP/1.1 400 
Content-Type: application/problem+json

{
  "detail": "zone must be a time zone region such as Asia/Kolkata or Europe/London, not \"IST\".",
  "instance": "/webinars",
  "status": 400,
  "title": "Unknown time zone"
}
```

### Case 10: webinar 99

**Why:** `404`.

Request

``` code
GET /webinars/99 HTTP/1.1
```

Response

``` code
HTTP/1.1 404 
Content-Type: application/problem+json

{
  "detail": "No webinar 99.",
  "instance": "/webinars/99",
  "status": 404,
  "title": "Webinar not found"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                                                  | What happens                                                        | Proved by                                |
|---------------------------------------------------------------------------------------|---------------------------------------------------------------------|------------------------------------------|
| Created in India, viewed in Los Angeles                                               | The evening before, 20:30                                           | `createdInTheHostZoneAndShownInAnyOther` |
| Starts this minute, or the next                                                       | `422`, then `201` (fixed Clock)                                     | `theFirstMinuteThatCountsIsTheClocks`    |
| A skipped time, US and UK                                                             | `422`                                                               | `aTimeTheClocksSkipIsRefused`            |
| A repeated time, with and without offset                                              | `422`; `201` with the right offset; `422` with a wrong one          | `aTimeThatHappensTwiceNeedsAnOffset`     |
| Monthly from the 31st; leap year                                                      | Month ends kept; 29 Feb 2028                                        | `monthlyFromThe31stKeepsToTheMonthEnd`   |
| Last Friday of each month                                                             | 30 Oct, 27 Nov, 25 Dec; a date that is not the last Friday is `422` | `lastFridayOfEachMonth`                  |
| IST, +05:30, a non-ISO date, 10 minutes, 13 sessions, unknown repeat, bad viewer zone | `400`                                                               | `brokenRequestsAre400`                   |
| Unknown webinar                                                                       | `404`                                                               | `unknownWebinarsAre404`                  |

## The trap

Plausible but wrong

Storing `LocalDateTime` without a zone, so times shift for other countries.

The old code is kept in the tests as `OldWebinarStore`, in both versions. The first stored `LocalDateTime`: asked for London, it can only answer 10:00, because the zone was never kept. The second stored an `Instant` but added months in UTC: a New York session at 10:00 on 20 October came back at 09:00 on 20 November, after the US left daylight saving. The fixed API runs the same two webinars and gets 04:30 for London, and 10:00 for the New York host in both months.

While building, each part was undone once. Adding 30 days instead of a month turned 2 tests red; dropping the "happens twice" check, 1; showing the host's time to the viewer, 3; repeating in UTC, 2; asking `Instant.now()` instead of the `Clock`, 1 (the fixed-clock test); accepting offsets and abbreviations as zones, 1.

``` code
package com.taskloom.webinars;

import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/** The first test written for this station: both bugs from the support tickets, then the same webinars through the fixed API. */
class LocalDateTimeTrapTest extends ApiTest {

    @Test
    void aLocalDateTimeShowsTenOClockToEveryone() throws Exception {
        var old = new OldWebinarStore.OldWebinar("Planning your first sprint", LocalDateTime.parse("2026-11-05T10:00"));
        assertThat(old.showTo("Europe/London")).isEqualTo(LocalDateTime.parse("2026-11-05T10:00"));   // 10:00 in London: wrong by 5h30

        String url = created(webinar("2026-11-05T10:00", "Asia/Kolkata", ""));
        mvc.perform(get(url).param("viewerZone", "Europe/London"))
                .andExpect(jsonPath("$.sessions[0].startsAt").value("2026-11-05T04:30:00Z"))
                .andExpect(jsonPath("$.sessions[0].hostTime").value("2026-11-05T10:00:00+05:30"))
                .andExpect(jsonPath("$.sessions[0].viewerTime").value("2026-11-05T04:30:00Z"));
    }

    @Test
    void repeatingInUtcMovesANewYorkSessionWhenDaylightSavingEnds() throws Exception {
        // 10:00 in New York on 20 Oct is 14:00 UTC. The US leaves daylight saving on 1 Nov 2026.
        var old = OldWebinarStore.monthlyInUtc(Instant.parse("2026-10-20T14:00:00Z"), 2);
        assertThat(old.get(1).atZone(ZoneId.of("America/New_York")).toLocalTime()).hasToString("09:00");   // the host's 10:00 became 09:00

        String url = created(webinar("2026-10-20T10:00", "America/New_York", ",\"repeat\":\"MONTHLY\",\"sessions\":2"));
        mvc.perform(get(url).param("viewerZone", "Asia/Kolkata"))
                .andExpect(jsonPath("$.sessions[1].hostTime").value("2026-11-20T10:00:00-05:00"))     // still 10:00 for the host
                .andExpect(jsonPath("$.sessions[0].viewerTime").value("2026-10-20T19:30:00+05:30"))
                .andExpect(jsonPath("$.sessions[1].viewerTime").value("2026-11-20T20:30:00+05:30"));  // an hour later in India, correctly
    }
}
```

``` code
package com.taskloom.webinars;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.stream.IntStream;

/** The scheduling code as it shipped, kept only in tests. */
class OldWebinarStore {

    /** Stored a LocalDateTime: 10:00, with no idea where. Every viewer got the same 10:00. */
    record OldWebinar(String title, LocalDateTime startsAt) {
        LocalDateTime showTo(String viewerZone) {
            return startsAt;   // nothing to convert from: the zone was never kept
        }
    }

    /** The later version stored an Instant, but repeated it by adding months in UTC, not in the host's zone. */
    static List<Instant> monthlyInUtc(Instant first, int count) {
        return IntStream.range(0, count).mapToObj(i -> first.atZone(ZoneOffset.UTC).plusMonths(i).toInstant()).toList();
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                         | Check with      |
|----------|-------------------------------------------------|-----------------|
| JDK      | 25 (recommended). JDK 21 also works, see below  | `java -version` |
| Maven    | Not needed: the project ships the Maven wrapper |                 |
| Docker   | Not needed for this station                     |                 |

**macOS / Linux**

``` code
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 10 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`; `@TestBean` needs Spring Framework 6.2 or later, which Boot 4 brings.

## Try it yourself

In `Schedule`, replace `startsAt.plusMonths(i)` with `startsAt.plusDays(30L * i)` and run:

``` code
./mvnw test -Dtest=WebinarContractTest#monthlyFromThe31stKeepsToTheMonthEnd
```

"A month" is not 30 days: the sessions drift off the month end. Put it back.

## Troubleshooting

| You see                                               | Cause                                                | Fix                                                                     |
|-------------------------------------------------------|------------------------------------------------------|-------------------------------------------------------------------------|
| The same time shown in every country                  | A `LocalDateTime` stored without a zone.             | Store an `Instant` and the host's zone.                                 |
| A repeating session moves by an hour for its host     | Repeated in UTC (or by adding hours).                | Add months or weeks to the local time, then resolve in the host's zone. |
| `Unknown time zone` for `IST`                         | Abbreviations are ambiguous and not region ids.      | Send `Asia/Kolkata`.                                                    |
| A test fails only after a certain date                | It asked the real clock.                             | Inject a `Clock`; fix it in tests with `@TestBean`.                     |
| Feb 28, Mar 28, Apr 28 for a 31st-of-the-month series | Months added to the previous session, not the first. | `first.plusMonths(i)`.                                                  |

## Project layout

``` tree
stations/051-webinar-scheduling-across-time-zones/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/taskloom/webinars/
│   ├── WebinarController.java   ├── Schedule.java   └── WebinarsApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/taskloom/webinars/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/taskloom/webinars/WebinarController.java`

Does  
Validates the body; accepts only region zone ids; reads `viewerZone`.

Why  
Zones checked at the edge, with a reason.

Without it  
"IST" meaning three countries.

#### `src/main/java/com/taskloom/webinars/Schedule.java`

Does  
Turns each session's wall-clock time into a moment in the host's zone, and moments into anyone's time.

Why  
One place knows about gaps, overlaps, month ends and the Clock.

Without it  
Times that shift abroad or at daylight saving.

- `getValidOffsets` returns 0 offsets in a gap and 2 in an overlap; both are refused unless the client chose.
- Monthly sessions are `startsAt.plusMonths(i)` from the first date, never chained: 31 Jan → 28 Feb → 31 Mar.
- `TemporalAdjusters.lastInMonth` finds the last Friday.

#### `src/main/java/com/taskloom/webinars/WebinarsApplication.java`

Entry point and the `Clock` bean (UTC); tests replace it.

#### `src/main/resources/application.yaml`

Problem details on; decimals refused for whole-number fields.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                              | Test class                  | Result |
|---------------|------------------------------------------|-----------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found | `WebinarContractTest` (8)   | pass   |
| Every station | Reproduce the failure before the fix     | `LocalDateTimeTrapTest` (2) | pass   |

## A clock the tests control

`ApiTest` replaces the app's `Clock` bean with `@TestBean`: "now" is 16 Oct 2026, 06:00 UTC, in every run. That is what lets one test say exactly which minute has started, and keeps the suite green next year.

## Run output

JDK 25.0.1, Spring Boot 4.1.1. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 8, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.webinars.WebinarContractTest
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.taskloom.webinars.LocalDateTimeTrapTest
[INFO] Tests run: 10, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/taskloom/webinars/LocalDateTimeTrapTest.java`

Written first: both old versions, and the same webinars through the fixed API.

#### `src/test/java/com/taskloom/webinars/WebinarContractTest.java`

Zones, the Clock, gaps, overlaps, month ends, last Fridays, and every refusal.

#### `src/test/java/com/taskloom/webinars/OldWebinarStore.java`

The old code, kept only in tests.

#### `src/test/java/com/taskloom/webinars/ApiTest.java`

Shared setup: the fixed Clock and a webinar body.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/taskloom/webinars/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=WeeklyChallengeTest`.
3.  Change the code until it passes, then run `./mvnw test` to check the other 10 tests.

Checked (`docs/challenge-run.txt`): with the reference solution copied in, all 12 tests pass (10 station tests and 2 challenge tests).

Challenge 1 · Beginner-friendly · about 15 minutes

## Weekly webinars

Add `"repeat": "WEEKLY"`: same weekday, same wall-clock time for the host, every week. Across 1 Nov 2026 a New York series stays at 10:00 for the host and moves by an hour in India.

**Done when:** the test in `WeeklyChallengeTest` passes.

Hints

- `startsAt.plusWeeks(i)` on the local time, then resolve as for every session.
- Seven times 24 hours would be wrong in the week the clocks change.

#### `challenge/WeeklyChallengeTest.java`

``` code
package com.taskloom.webinars;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: "repeat": "WEEKLY" — same weekday, same wall-clock time for the host, every week. A New York series
 * across 1 Nov 2026 (the US leaves daylight saving) stays at 10:00 for the host and moves by an hour in India.
 */
class WeeklyChallengeTest extends ApiTest {

    @Test
    void weeklyKeepsTheHostsWallClock() throws Exception {
        String url = created(webinar("2026-10-27T10:00", "America/New_York", ",\"repeat\":\"WEEKLY\",\"sessions\":2"));
        mvc.perform(get(url).param("viewerZone", "Asia/Kolkata")).andExpect(status().isOk())
                .andExpect(jsonPath("$.sessions[*].hostTime", contains("2026-10-27T10:00:00-04:00", "2026-11-03T10:00:00-05:00")))
                .andExpect(jsonPath("$.sessions[*].viewerTime", contains("2026-10-27T19:30:00+05:30", "2026-11-03T20:30:00+05:30")));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 20 minutes

## The viewer's day and end time

Show each session's `viewerEndTime` (start plus duration, in the viewer's zone) and `viewerDayShift`: the viewer's date minus the host's (−1 for "the evening before").

**Done when:** the test in `ViewerDayChallengeTest` passes.

Hints

- Add the duration to the instant, then convert: never to a local time.
- `ChronoUnit.DAYS.between(hostDate, viewerDate)`.

#### `challenge/ViewerDayChallengeTest.java`

``` code
package com.taskloom.webinars;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 2: each session also shows "viewerEndTime" (start plus the duration, in the viewer's zone) and
 * "viewerDayShift": the viewer's calendar date minus the host's (-1 means "the evening before" for the viewer).
 */
class ViewerDayChallengeTest extends ApiTest {

    @Test
    void theViewerSeesTheirOwnDayAndEnd() throws Exception {
        String url = created(webinar("2026-11-05T10:00", "Asia/Kolkata", ""));
        mvc.perform(get(url).param("viewerZone", "America/Los_Angeles"))
                .andExpect(jsonPath("$.sessions[0].viewerEndTime").value("2026-11-04T21:30:00-08:00"))
                .andExpect(jsonPath("$.sessions[0].viewerDayShift").value(-1));
        mvc.perform(get(url).param("viewerZone", "Pacific/Auckland"))
                .andExpect(jsonPath("$.sessions[0].viewerTime").value("2026-11-05T17:30:00+13:00"))
                .andExpect(jsonPath("$.sessions[0].viewerDayShift").value(0));
        mvc.perform(get(url)).andExpect(jsonPath("$.sessions[0].viewerDayShift").value(0));
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## When a country changes its clocks

A government announces, six months ahead, that it will stop daylight saving. Webinars in that zone are already stored as instants. Which ones are now wrong, how would you find them, and would storing the host's local time and zone (and computing the instant later) have been better for future events?

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test with both old versions.
2.  Decide what the client sends (wall-clock time and zone) and what the server keeps (moment and zone).
3.  Resolve every session on its own date; refuse gaps and overlaps unless the client is explicit.
4.  Inject a `Clock`, and pin it in tests.

## Design alternatives and trade-offs

| Approach                                                      | What it costs                                                                  | Verdict                      |
|---------------------------------------------------------------|--------------------------------------------------------------------------------|------------------------------|
| Store `Instant` + host zone; resolve each session in the zone | Zone rule changes after creation are not followed.                             | Chosen                       |
| Store `LocalDateTime` only                                    | No moment at all: wrong for everyone elsewhere.                                | The trap                     |
| Store local time + zone; compute the instant on read          | Follows rule changes; every read recomputes, and sorting by moment needs care. | Better for far-future events |
| Store `OffsetDateTime`                                        | Keeps one offset; a series cannot follow daylight saving.                      | For past events              |
| Silently shift gap times (Java's default)                     | 02:30 becomes 03:30 without anyone choosing it.                                | Surprising                   |

## Database design

None in this station. In PostgreSQL, a moment is a `timestamptz` column (stored as UTC), and the host's zone a text column holding the region id. A `timestamp` column without time zone is this station's trap in SQL form.

# 3 · Go deeper: Production

Time zone data changes  
Governments change their rules several times a year somewhere. The JDK ships the IANA time zone database; keep the JDK updated, or use the tzupdater tool between releases.

Servers run in UTC  
Never rely on the server's default zone. Ask for a zone explicitly everywhere, as this code does.

Show offsets  
Times sent to clients carry their offset, so no client has to guess.

One clock  
Code that asks the real clock directly cannot be tested at midnight, at month end or on 29 February. Inject a `Clock`.

# 3 · Go deeper: Interview

## Interview takeaways

Instant, LocalDateTime, ZonedDateTime, OffsetDateTime: when each?

Instant for a moment (storage, logs). LocalDateTime for a wall-clock reading with no place (what a user types). ZonedDateTime for a moment in a region with rules, for arithmetic across daylight saving. OffsetDateTime for a moment with a fixed offset, for sending over the wire.

What happens with 02:30 on a spring-forward night?

It does not exist. getValidOffsets returns nothing; ZonedDateTime.of would silently move it forward. Decide: refuse it, or move it on purpose.

Why not add 24 hours to get tomorrow at the same time?

On a daylight saving day, a day is 23 or 25 hours. Add a day to the local date-time, then resolve it in the zone.

How do you test code that depends on the current time?

Inject java.time.Clock and call LocalDate.now(clock) or clock.instant(). In tests, use Clock.fixed, here through Spring's @TestBean.

What is Jan 31 plus one month?

Feb 28 (29 in a leap year): plusMonths clamps to the month end. Always add from the original date for a series, or you get stuck on the 28th.

## Self-check rubric

| Area            | Meets the bar                          | Above the bar                                       |
|-----------------|----------------------------------------|-----------------------------------------------------|
| Correctness     | All 10 tests pass.                     | You broke the month arithmetic and watched it fail. |
| Types           | The right java.time type at each step. | You can explain why the response carries offsets.   |
| Daylight saving | Gaps and overlaps refused.             | You can argue for refusing vs shifting.             |
| Testing         | A fixed Clock.                         | No test depends on today's date.                    |

# 3 · Go deeper: Review

## No reviewer view for this station

This Foundations station has no flawed version to review. Use this checklist on any code with dates and times:

- Is there a `LocalDateTime` stored or sent without a zone?
- Is date arithmetic done in the zone that the rule belongs to?
- What does the code do at 02:30 on a spring-forward night?
- Does anything call `now()` without a `Clock`?
