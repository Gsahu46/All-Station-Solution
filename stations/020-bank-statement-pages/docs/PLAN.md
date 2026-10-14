# Station 020 plan: Bank statement pages

**Problem.** Tijori's statement endpoint returns any page size it is asked for: 4,000 transactions time out on phones,
and size=1,000,000 loaded everything. page x size is an int, so a huge page number overflows into a 500.

**Endpoint.** `GET /accounts/{id}/transactions?page&size` (page from 0, size 1-100, default 20; page x size under
10,000, a demo rule) 200 with a Page; 400 out of range or too deep; 404 unknown account. Past the end: empty page.

**Data.** No database. acc-1001: 4,000 generated transactions (seed 20); acc-1002: none. Statement order: a Comparator
chain, postedAt desc then id desc (up to 19 rows share a minute). `record Page<T extends Page.Identified>` with
`of(sorted, page, size)` using a long offset, and `lastId()` (needs the bound).

**Trap.** `BottomlessPageTrapTest`: old paging returns all 4,000 for size 1,000,000; page 200,000,000 x 20 is a
negative int and throws; the fixed endpoint gives 400 for both. Mutations: no @Max -> 2 red; int offset -> the real
IndexOutOfBoundsException saved in docs/int-offset-run.txt; no tie-breaker -> 2 red.

**Tests.** Trap, `StatementContractTest`, `PageTest` (walk every page at sizes 1/7/37/100, tie order, empty list,
another Identified type).

**Practice.** 1: from/to date range. 2: sort=largest with a three-step Comparator chain.
Design: why offsets break on live data (see the keyset station).
