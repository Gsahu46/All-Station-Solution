# Station 059 plan: Loyalty points tested on real PostgreSQL

**Problem.** Basketo's loyalty code used H2's upsert, MERGE INTO ... (columns) KEY (...) VALUES. The test suite ran on
in-memory H2 (in PostgreSQL mode) and passed; production PostgreSQL rejected the statement on the first earn.

**Endpoints.** `POST /loyalty/{customerId}/earn` {orderRef, amountPaise} 201 {earned, balance}: 1 point per full ₹100
(demo rule); 409 the order already earned (case-insensitive); 404 unknown customer; 400 malformed.
`POST /loyalty/{customerId}/redeem` {points} 200; 422 not enough points; 404; 400.

**Code.** LoyaltyLedger: ledger entry + PostgreSQL upsert (INSERT ... ON CONFLICT (customer_id) DO UPDATE SET points =
point_balances.points + EXCLUDED.points RETURNING points) in one transaction; redeem is a conditional UPDATE ...
RETURNING.

**Database.** point_balances_not_negative, point_balances_customer_fk, point_entries_customer_fk,
point_entries_reason_known, point_entries_sign_matches, point_entries_order_once.

**Tests.** All on real PostgreSQL via @SpringBootTest + @ServiceConnection; @Testcontainers(disabledWithoutDocker =
true) skips them when Docker is missing (docs/no-docker-run.txt: Docker stopped, 11 skipped, 0 failed, 0 passed).
Isolation: each test makes its own customers. H2VersusPostgresTrapTest (old MERGE passes on H2, PostgreSQL: syntax
error at "("; H2 cannot even parse the new upsert), LoyaltyContractTest, LoyaltyDatabaseTest (constraints; rollback
of both rows; 20 earns at once for a new customer add up). Mutations: old MERGE -> 5 red; replace instead of add -> 2;
unconditional redeem -> 1.

**Practice.** 1: balance with ledger. 2: reversal of an order's points (V3 migration). Design: when an in-memory
database is still fine.
