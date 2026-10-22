# Station 089 plan: App config with HTTP caching

**Problem.** Streamo (fictional): 20 million app launches a day each download the same 40 KB config, and old app
versions that must update cannot be told.

**Endpoint.** `GET /app-config?platform=android|ios&version=x.y.z`: 200 with updateRequired (below the minimum
supported version), updateAvailable, latest and minimum versions, features, home rails, endpoints; `ETag` (SHA-256 of
the answer's JSON, 22 base64url characters, quoted) and `Cache-Control: max-age=300, public` (demo rule). If-None-Match
matching (weak comparison, lists) -> 304 with the same ETag and Cache-Control, no body. Platform case-insensitive
(Locale.ROOT), version three numbers; anything else 400.

**Versions.** `AppVersion` compares number by number: as text, 5.10.0 < 5.9.0.

**Trap.** `EveryLaunchDownloadsTrapTest`: 20 launches without If-None-Match download 20 times the body; with the ETag,
once and then 19 empty 304s.

**Found while building.** (1) Spring compares If-None-Match itself when the ResponseEntity has an ETag, and keeps
Cache-Control on the 304: no checkNotModified code needed. (2) If-None-Match: * is answered 200 (seen in tests and on
the running app); RFC 9110 13.1.2 calls for 304. Apps never send it; recorded in a test.

**Mutations.** no ETag -> 4; no Cache-Control -> 2; a fixed ETag -> 3; versions compared as text -> 1; platform not
lower-cased -> 1; <= instead of < for the minimum -> 1.

**Review.** serverTime in the body (a new ETag every request) and a one-day max-age. 3 of 8 fail.

**Practice.** 1: Last-Modified and If-Modified-Since. 2: a 10% rollout by bucket that keeps ETags shared.
3 (paper): a CDN in front, and forcing an update before max-age ends.
