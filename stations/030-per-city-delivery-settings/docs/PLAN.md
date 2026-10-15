# Station 030 plan: Per-city delivery settings

**Problem.** Basketo's per-city radius, fee and minimum order live in configuration with no checks: a typo
("minimun-order-paise") left the minimum at 0 in one city and nothing failed. The delivery check also trusted the
distance the client sent.

**Endpoints.** `GET /cities/{city}/delivery-terms` 200 / 404. `POST /delivery-checks` {city, lat, lon, orderPaise}
200 with the server's distance, deliverable and reasons (OUT_OF_RANGE, BELOW_MINIMUM); 404 unknown city; 400 bad
fields, including a client-sent distanceKm (fail-on-unknown-properties).

**Data.** No database. `@ConfigurationProperties(prefix="basketo", ignoreUnknownFields=false) @Validated record
DeliverySettings(Map<String, City>)`; wrapper types + @NotNull so a missing value is null, never 0; @Min(9900) floor
(demo). `application-dev.yaml` adds a test city. Env vars override via relaxed binding. Default `DistanceCalculator`
in a real `@AutoConfiguration` with @ConditionalOnMissingBean (haversine, R = 6371.0088 km).

**Trap.** `UnvalidatedConfigTrapTest`: old primitives-only settings start with the typo and a 0 minimum; the real
settings refuse to start; the old check trusted a client's 0 km. Mutations: no @Validated -> 2 red; unknown fields
allowed -> 1 red. Default as a plain scanned @Configuration: not caught by the test in this arrangement (an earlier
nested version did create both beans); documented, not claimed.

**Tests.** Trap, `DeliveryContractTest`, `DeliveryConfigTest` (bad values, extra key, env var, dev profile, own bean
replaces the default, Pune to Mumbai 120.15 km).

**Practice.** 1: free delivery above a threshold (cross-field @AssertTrue). 2: fee by distance band.
Design: configuration you can change without a restart.
