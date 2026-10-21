# Station 078 plan: Customers see only their own accounts

**Problem.** Tijori's statement page looked accounts up by the id in the URL; account numbers count up, so changing
1001 to 1002 showed another customer's statement (IDOR).

**Endpoints.** HTTP Basic against the customers table (bcrypt), stateless. `GET /accounts/{id}`: id, kind, name,
balance (paise), this sign-in's access. `GET /accounts/{id}/statements?month=YYYY-MM`: lines, opening and closing
balance. Not a holder or not existing: the same 404. A balance-only holder asking for statements: 403 (a holder may
know the account exists). Bad id or month: 400. Everything else denyAll.

**Authorisation in the query.** The account query joins account_holders and customers on the signed-in email: the
URL's id is half the WHERE clause. Joint accounts have two full holders; a shop assistant is balance_only. The lines
query repeats the ownership join (defence in depth). The statement runs in one REPEATABLE READ read-only transaction.

**Database.** customers (email lower/unique, bcrypt shape); accounts (kind, balance >= 0); account_holders (PK
account+customer, access full|balance_only); transactions (amount <> 0, description 1-140). Demo September 2026 data.

**Trap.** `UrlIdTrustTrapTest`: the old lookup returns Dev's account to Zoya; the API says 404; walking 1000-1005
finds only Zoya's 1001 and 1003, others look like non-existent ones; the control works.

**Found while building.** (1) The first demo balances made September's opening balance negative: the August test
caught it. (2) The repeated ownership join in the lines query turned no test red when removed (account() already
refuses). (3) REPEATABLE READ is untested: no test makes a payment commit between the statement's queries.

**Mutations.** id trusted (holder join made always true) -> 4; no balance-only check -> 1; lines without ownership
join -> 0; READ COMMITTED -> 0 (untested); denyAll -> authenticated() -> 1.

**Review.** Look up by id, then a holder check that answers 403 "belongs to another customer" (the numbers now
reveal which accounts exist), and statements for balance-only holders: 4 of 16 fail.

**Practice.** 1: GET /accounts, the customer's own list. 2: CSV statement with the same rules; rupees from paise with
BigDecimal; quoting. 3 (paper): bank staff access with consent and audit.
