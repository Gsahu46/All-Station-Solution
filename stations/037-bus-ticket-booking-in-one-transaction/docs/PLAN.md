# Station 037 plan: Bus ticket booking in one transaction

**Problem.** Safarbus saved a booking, then its passengers, each statement auto-committed. A crash or a failed
passenger insert between them left bookings with no (or only some) passengers, charged in full.

**Endpoint.** `POST /bookings` {tripId, contactPhone, passengers[1..6]{name, age, seatNo}} 201 {bookingId, tripId,
seats, totalPaise, status CONFIRMED}; 404 trip; 409 seat already booked (nothing saved, seats named); 422 seat beyond
the bus or the same seat twice; 400 bad body. A booking record is created; no payment is taken.

**Code.** Plain JDBC in `BookingStore.save`: `setAutoCommit(false)`; insert booking with generated key ("id");
passengers as one `addBatch`/`executeBatch`; `commit`; on any SQLException or RuntimeException `rollback`; finally
`setAutoCommit(true)`. A 23505 on `booking_passengers_seat_once` becomes 409.

**Database.** trips, bookings (phone check, total > 0, UNIQUE (id, trip_id)), booking_passengers (PK booking+seat,
composite FK (booking_id, trip_id), UNIQUE (trip_id, seat_no) `booking_passengers_seat_once`, seat/age/fare checks).

**Trap.** `AutoCommitTrapTest`: old code + a crash between inserts -> a booking with no passengers; a taken seat
halfway -> a booking with one of two passengers; the real store, same failure -> nothing. Mutations: auto-commit
left on -> 8 red; no rollback -> 1 (only a Java error midway shows it: PostgreSQL will not commit a transaction that
had an error, but setAutoCommit(true) commits a clean one); finally not restoring auto-commit -> not caught
(HikariCP resets it on return), kept so the code does not rely on the pool.

**Database tests.** constraints without Java, seat once per trip, a dead (aborted) connection commits nothing, a
refused passenger rolls back the booking, a Java error midway rolls back, generated ids and batch rows.

**Practice.** 1: cancel in one transaction. 2: senior fares per passenger, total = sum. Design: holding a seat
while the customer pays.
