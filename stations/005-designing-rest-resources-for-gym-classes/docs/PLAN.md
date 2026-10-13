# Station 005 plan: Designing REST resources for gym classes

**Problem.** FitNest's booking API uses verb URLs (/bookClass, /cancelBooking) and answers 200 + success:false to
everything; the app cannot tell full from already-booked from unknown class.

**Endpoints.** `GET /classes?date` 200 (400 missing/non-ISO date) · `POST /classes/{id}/bookings` 201 + Location, 400
unknown/missing member, 404 class, 409 full / already booked · `GET /bookings/{id}` 200/404 · `DELETE /bookings/{id}` 204/404
· `GET /members/{id}/bookings` 200/404.

**Data.** No database. Four classes (Morning Yoga capacity 2), three members, bookings in a synchronized LinkedHashMap.
`BookingOutcome` (sealed) keeps "what happened" apart from the status code.

**Trap.** Verb URLs + always 200. `VerbsAndAlways200TrapTest`: full, double booking, unknown class all 200/"Could not book"
on the old API; 409/409/404 on the new. Mutation: no capacity check -> 3 tests red.

**Tests.** `VerbsAndAlways200TrapTest`, `BookingContractTest`. No station types.

**Practice.** 1: GET /classes/{id}/bookings roster. 2: PATCH /classes/{id} capacity, 409 below bookings.
Design: 2-hour cancellation cutoff with a Clock and time zones.
