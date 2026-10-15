# Station 044 plan: Hotel room availability calendar

**Problem.** Ghoomo sold room 101 for 11-13 June while 10-12 June was booked: the clash check compared only start
dates.

**Endpoints.** `GET /rooms/{id}/availability?from&to` (nights from..to-1, at most 62) 200 {roomId, from, to,
freeNights, nights[{date, available}]}; 404 room; 400 to not after from. `POST /rooms/{id}/blocks` {checkIn,
checkOut, guestName} (check-out exclusive, 1 to 30 nights) 201 {id, roomId, checkIn, checkOut, nights, guestName};
409 Not available; 404; 400. A hold is a demo record.

**Rule.** Half-open [checkIn, checkOut). Overlap: existing.checkIn < new.checkOut AND existing.checkOut > new.checkIn,
as the derived JPA method existsByRoomIdAndCheckInBeforeAndCheckOutAfter. Database: room_blocks_no_overlap EXCLUDE
USING gist with daterange '[)', room_blocks_dates_order, FK.

**Found while building.** (1) A derived name ending in "CheckIn" reads "In" as the IN keyword: Spring Data looked
for a property "check"; the old method is named ...CheckInEquals. (2) Two overlapping inserts can deadlock on the
exclusion check; PostgreSQL aborts one (40P01), which was a 500 once in a build; PessimisticLockingFailureException
now maps to 409. Not reproducible on demand, so no test claims it.

**Trap.** `StartDatesOnlyTrapTest`: old start-date check says 11-13 free; inclusive-end check refuses a
back-to-back stay; 8 overlap shapes. Mutations: overlap arguments swapped -> not caught (the constraint turned
every clash into the same 409); constraint violation not mapped -> 2 errors (the race past the Java check is real);
calendar counts the check-out night -> 1; no EXCLUDE -> 4.

**Review.** start-date-only check, no mapping of the constraint, calendar inclusive, zero-night stays: 5 of 18 fail.

**Practice.** 1: cancel a block (404 for another room's). 2: free rooms by dates and guests (JPQL not exists).
