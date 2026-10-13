# Station 015 plan: Splitting a group bill

**Problem.** SplitSaathi splits with double and rounds each share: a paisa goes missing; settle-up replays every expense.

**Endpoints.** `POST /groups/{id}/expenses` (EQUAL / EXACT / SHARES) 201 with owedPaise; 400 bad fields; 422 invalid
split; 404. `GET /groups/{id}/settle-up` balances + greedy payments (at most n - 1).

**Data.** No database. Whole paise. Splitter.equal: quotient + remainder to the first listed; Splitter.shares: largest
remainder. Expenses store their split; balances = paid - owed, always zero-sum (SettleUp refuses otherwise).

**Trap.** double / rounded BigDecimal per share. `MissingPaisaTrapTest`: 999.99 from 1000; BigDecimal divide throws or
still loses the paisa; Splitter gives 33,334 + 33,333 + 33,333. Mutation: leftover paisa dropped -> 2 tests red.

**Tests.** Trap, `ExpenseContractTest`, `SplitterTest` (1,000 seeded random splits; settle-up clears all balances).

**Practice.** 1: PERCENT via Splitter.shares. 2: settlements recorded as an expense owed by the receiver.
Design: a fairer remainder rule.
