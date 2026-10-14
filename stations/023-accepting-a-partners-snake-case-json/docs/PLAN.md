# Station 023 plan: Accepting a partner's snake_case JSON

**Problem.** Dakroute's courier partner sends snake_case JSON with a local time and adds fields without notice. The
platform's Jackson config fails on unknown properties (strict for its own clients), so every new partner field turned
the webhook into 400s; a camelCase DTO on a lenient mapper read every field as null.

**Endpoint.** `POST /partner/delivery-updates` 202 with our camelCase event (times as UTC instants); 400 missing or
malformed fields (including the wrong time format or our own names); 404 an AWB we never booked. Unknown status code:
accepted as UNKNOWN with the raw code, and a warning logged.

**Data.** No database. `PartnerUpdate` with `@JsonNaming(SnakeCaseStrategy)` and `@JsonIgnoreProperties(ignoreUnknown)`,
class by class; `event_time` as `LocalDateTime` with `@JsonFormat("yyyy-MM-dd HH:mm:ss")`, converted with Asia/Kolkata;
`promised_by` ISO with offset -> Instant. Jackson 3 facts checked: a plain JsonMapper ignores unknown fields; offsets
are normalised to UTC.

**Trap.** `NewPartnerFieldTrapTest`: strict mapper throws on rider_phone; camelCase DTO reads nulls; endpoint accepts
the payload. Mutations: no ignoreUnknown -> 3 red; no snake_case -> many red; UTC instead of IST -> 2 red.

**Tests.** Trap, `DeliveryUpdateContractTest`, `JsonRulesTest` (the app's mapper: strict for our types, tolerant for partner).

**Practice.** 1: duplicate updates. 2: two time formats with a ValueDeserializer. Design: versioning a partner contract.
