# Station 019 plan: A Money type for a multi-currency wallet

**Problem.** Tijori's wallet keeps one BigDecimal balance, so rupees were added to dollars; amounts compared with
`BigDecimal.equals` treated Rs 10.5 and Rs 10.50 as different.

**Endpoints.** `POST /wallets/{id}/credits` (amount as a decimal string, currency ISO code, reference) 201 with the
credit and that currency's balance; 400 bad shape; 422 unsupported currency, too many decimals, zero; 404 unknown
wallet. `GET /wallets/{id}/balance` one balance per currency, never added together.

**Data.** No database. `record Money(long minorUnits, Currency currency)`: parse via `setScale(defaultFractionDigits)`
with no rounding mode (refuses lost digits); `plus` refuses another currency; `Math.addExact`. Wallet = ConcurrentHashMap
per currency, `merge(currency, credit, Money::plus)`.

**Trap.** `RupeesPlusDollarsTrapTest`: old balance "105"; `equals` false and a HashSet of 2 for 10.5/10.50; Money equal
with one set entry; wallet keeps INR and USD apart. Mutations: no currency check -> 1 red; silent rounding -> 2 red;
one key for all currencies -> Money itself refuses (CurrencyMismatchException).

**Tests.** Trap, `WalletContractTest`, `MoneyTest` (equality, mismatch, immutability, decimals per currency, overflow).

**Practice.** 1: debits, never below zero. 2: indicative total at demo rates, half-even per balance.
Design: storing Money in a database.
