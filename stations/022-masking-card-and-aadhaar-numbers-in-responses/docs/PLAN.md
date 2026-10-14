# Station 022 plan: Masking card and Aadhaar numbers in responses

**Problem.** Tijori's profile API returns full card, Aadhaar, account and mobile numbers; the app masks them on screen,
but responses end up in logs, proxies, crash reports and screenshots.

**Endpoint.** `GET /customers/{id}/profile` (HTTP Basic, demo users) 200 masked profile; 401 no or wrong credentials;
403 marketing role; 404 unknown id or someone else's (same answer). Support reads any profile, masked the same.

**Data.** No database. `record Sensitive(Kind, raw)` with class-level `@JsonSerialize(using = MaskingSerializer)`
(Jackson 3 `ValueSerializer`) and a masked `toString()`. Kinds: AADHAAR XXXX XXXX 0123, CARD XXXX XXXX XXXX 1111,
ACCOUNT/MOBILE last 4, EMAIL a***@domain. No CVV stored.

**Trap.** `FullNumberTrapTest`: plain-string profile serialises and prints the full numbers; the real response has none
and no 5-digit run; a plain JsonMapper masks too (rule on the type).

**Tests.** Trap, `ProfileContractTest`, `ProfileSecurityTest` (401, 403, cross-customer 404 identical to missing,
support still masked, no unmask parameter, malicious ids, firewall), `MaskingTest`.

**Review.** review/Sensitive.java (Aadhaar shows the first 4; toString removed) and review/ProfileController.java
(?full=true for support; no ownership check): 7 of 15 tests fail.

**Practice.** 1: PAN. 2: verify the last 4 without revealing. Design: who may ever see a full number.
