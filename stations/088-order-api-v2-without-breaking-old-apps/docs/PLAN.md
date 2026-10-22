# Station 088 plan: Order API v2 without breaking old apps

**Problem.** Kartwala (fictional) renamed `customerName` to `customer.name` (and `qty`, `total`, the states) in place.
Apps up to 5.x, 30% of users, could not read orders for two days.

**Endpoints.** `GET /v1/orders/{id}`: the frozen v1 shape (customerName, total in rupees as an exact decimal, items
with qty and price, upper-case status, trackingUrl added later); every answer carries Deprecation (RFC 9745,
Proposed Standard), Sunset (RFC 8594, Informational) and Link rel="deprecation". `GET /v2/orders/{id}`: the new
shape (customer object, paise, quantity, lower-case status, placedAt), no deprecation headers. 404 unknown order,
400 bad id or unknown version.

**Versioning.** Spring Framework 7: `@GetMapping(path = "/{version}/orders/{id}", version = "1")`,
`ApiVersionConfigurer.usePathSegment(0)`, `StandardApiVersionDeprecationHandler` with demo dates (deprecated 1 Oct 2026,
sunset 1 Apr 2027 IST). One model (`Orders.Order`), one record per version.

**Trap.** `RenameInPlaceTrapTest`: app 5.x's own model reads the renamed shape and fails (Jackson 3 refuses a missing
int); a reader that lets it pass shows no customer and no total. v1 still reads completely. An added field
(trackingUrl) is compatible for a tolerant reader and breaks a strict one.

**Found while building.** (1) Spring wrote the Sunset date with the zone's offset (+0530): HTTP dates are GMT, so the
date is configured in UTC. (2) The old app's failure was a crash, not an empty name: qty renamed to quantity left a
missing int. (3) The version parser accepts 1, v1 and v1.0 as the same version.

**Mutations.** v1 field renamed -> 3; v1 total in paise -> 2; v1 status lower case -> 2; v1 field removed -> 1; no
deprecation headers -> 1; Sunset in IST -> 1; v2 status upper case -> 1.

**Review.** "Paise everywhere" and "one way to write states": v1's total becomes paise under the same name and its
status lower case. 2 of 7 fail; the old app reads ₹1,29,950 without an error.

**Practice.** 1: 410 Gone after the sunset. 2: dated versions in a header, Stripe style. 3 (paper): versioning a write
endpoint, and when to stop supporting v1.
