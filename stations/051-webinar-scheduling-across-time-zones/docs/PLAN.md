# Station 051 plan: Webinar scheduling across time zones

**Problem.** Taskloom stored a webinar's start as a LocalDateTime: a 10:00 IST webinar showed as 10:00 in London.
The next version stored an Instant but repeated series by adding months in UTC, so after the US left daylight saving
a 10:00 New York session moved to 09:00 for its host.

**Endpoints.** `POST /webinars` {title, startsAt (host wall-clock, no offset), zone (region id), durationMinutes
15-480, repeat NONE | MONTHLY | MONTHLY_LAST_WEEKDAY, sessions 1-12, offset (only for a time that happens twice)} 201
+ Location; `GET /webinars/{id}?viewerZone` each session as startsAt (UTC), hostTime and viewerTime (with offsets).
400: malformed, unknown zone (IST, +05:30 refused: only region ids). 422: start not after the Clock's now, a time in
a DST gap, a time in an overlap without (or with a wrong) offset, NONE with more than one session, LAST_WEEKDAY on a
date that is not the last such weekday. 404 unknown.

**Code.** Schedule resolves each session's local time in the host zone with getValidOffsets (0 = gap, 2 = overlap);
monthly sessions are startsAt.plusMonths(i) from the first date (Jan 31 -> Feb 28/29 -> Mar 31), last-weekday ones
use TemporalAdjusters.lastInMonth. Stored: host zone and instants. Clock bean; tests replace it with @TestBean.

**Tests.** LocalDateTimeTrapTest (old LocalDateTime shows 10:00 in London; old UTC repeat turns New York 10:00 into
09:00; the fixed API shows 04:30 London and 19:30 -> 20:30 India), WebinarContractTest. Mutations: 30 days instead of a
month -> 2 red; no overlap check -> 1; viewer shown host time -> 3; series repeated in UTC -> 2; Instant.now() instead
of the Clock -> 1; offsets accepted as zones -> 1.

**Practice.** 1: weekly repeat across DST. 2: viewer's end time and day shift. Design: storing future events as
local time + zone vs instant when governments change time zone rules.
