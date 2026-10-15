# Station 050 plan: Hotel booking request validation

**Problem.** Ghoomo's booking requests were validated field by field: check-out before check-in passed (both dates in
the future), and 6 guests in a 2-person room passed (each count within its range).

**Endpoint.** `POST /hotel-bookings` {hotelId, roomType, checkIn, checkOut, adults 1-10, children 0-10 (optional),
guestName, phone} 201 + Location, a request record (no room held, nothing paid). Added `GET /hotel-bookings/{id}` to
read it back, so the "not found" case has a resource (404). 400: a field broken on its own (Default group, @Valid,
errors map). 422: fields valid alone but not together (Consistency group, run by the service): stay rules (check-in
today or later in IST and at most 365 days ahead, check-out after check-in, at most 30 nights) and room rules (hotel
exists, room type exists, adults + children within what it sleeps). Cross-field rules never run while a field is
broken.

**Code.** Custom ConstraintValidators: @IndianMobile (field), @ValidStay and @RoomFitsGuests (class level, Spring-made
so they get the Clock and the catalogue, violations put on the field they concern). Room types normalised with
Locale.ROOT. No database: an in-memory catalogue and request store (demo).

**Tests.** FieldByFieldTrapTest (old request passes the app's validator for both tickets; the API answers 422 naming
the field), BookingContractTest (valid and read back, normalising on a Turkish default locale, 400s, 422s, edges, a
broken field reported alone, 404), BookingValidatorTest (groups, mobile formats). Mutations: no @ValidStay -> 3 red;
no @RoomFitsGuests -> 3; default locale -> 1; room rules in the Default group -> 5.

**Practice.** 1: child ages, one per child (field 400 vs list-size 422). 2: optional GSTIN with a check character
(field-level validator). Design: where validation belongs (client, controller, service, database).
