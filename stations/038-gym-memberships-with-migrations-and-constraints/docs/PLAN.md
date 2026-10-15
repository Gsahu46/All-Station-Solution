# Station 038 plan: Gym memberships with migrations and constraints

**Problem.** FitNest's version 1 schema had primary keys only; every rule was in Java. Another writer stored two
members with one phone (written two ways) and a membership that ends before it starts.

**Endpoints.** `POST /members` {name, phone} 201 {id, name, phone (10 digits)}; 409 phone already registered;
400 bad phone or name. `POST /members/{id}/memberships` {planCode, startsOn} 201 {id, memberId, planCode, startsOn,
endsOn (day before the same date next period), pricePaise}; 404 member; 422 unknown plan; 409 overlap; 400 bad body.

**Migrations.** V1 as shipped (kept, never edited). V2: `plans` table (3NF), phones normalised then
`members_phone_digits` + `members_phone_unique`, memberships get `plan_code` FK, member FK, `memberships_dates_order`,
price positive, then (its own ALTER) `memberships_no_overlap` EXCLUDE USING gist with btree_gist. The price stays on
the membership: what was paid, not a copy of the plan.

**Code.** JdbcClient (named parameters, RETURNING, records). Constraint names map to 409; Java does not ask first.

**Trap.** `JavaOnlyRulesTrapTest`: Flyway to V1 in schema v1_only; plain SQL stores a duplicate phone and inverted
dates; the V2 schema refuses both by name. Mutations: no unique phone -> 3 red; no overlap rule -> 2; phones not
normalised in V2 -> 1; duplicate phone not mapped -> 1; overlap not mapped -> 1.

**Database tests.** every named constraint, overlap vs back-to-back, rollback takes the new member, V2 meeting bad
data fails by constraint name and rolls back fully until the rows are fixed (found while building: in one ALTER the
EXCLUDE index fails on inverted dates with an unnamed range error, so it is a separate statement), history 1, 2.

**Practice.** 1: V3 email, unique in any case. 2: freeze up to 30 days (V4 check; the EXCLUDE guards the update).
Design: changing a constraint on a big table without downtime.
