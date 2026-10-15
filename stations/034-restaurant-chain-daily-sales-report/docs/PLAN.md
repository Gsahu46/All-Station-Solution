# Station 034 plan: Restaurant chain daily sales report

**Problem.** Tiffino's 40 outlet owners get totals from a hand-filled spreadsheet. The first automated version summed
rupees in double (293.9 * 100 = 29389.999999999996, cast to 29389 paise) and grouped bills by one reused mutable
key object, so every row was labelled with the last sale's outlet and hour.

**Endpoint.** `GET /reports/daily-sales?date=YYYY-MM-DD` 200 {date, chainTotalPaise, bills, outlets[{outletId,
name, totalPaise, bills, busiestHour}] highest first (ties by id), hours[{hour, totalPaise, bills}] in order};
404 no sales that day; 422 today or later (the day is not over in India); 400 missing or malformed date.

**Design.** `Sale(outletId, Instant at, BigDecimal amountRupees)` as a till exports it. Day = midnight to midnight
IST. `groupingBy` + `reducing` into an immutable `Totals(amount, bills)` record; composite key is a record
`OutletHour`; entries sorted with `comparingByValue().reversed().thenComparing(comparingByKey())`; paise via
`movePointRight(2).longValueExact()` (a fraction of a paisa is an error). `DemoSalesFeed`: 7 days of seeded bills
for 40 outlets, menu price + 5% GST.

**Trap.** `DoubleMoneyMutableKeyTrapTest`: old double total for TF-02 is 29,389 paise; the reused mutable key
labels every row "TF-03 20"; the real report is exact. Mutations: hours in UTC -> 2 red; day in UTC -> 4; ascending
-> 3; double sum -> 11; tie to later hour -> 1; today allowed -> 1.

**Tests.** Trap; `DailySalesReportTest` (IST edges, names, ties, a fraction of a paisa); `StreamsAndLoopAgreeTest`
(a loop over paise agrees on all 7 demo days); `DailySalesContractTest` (strict JSON, 404, 422, 400).

**Practice.** 1: weekly totals per outlet. 2: busiest hour per city (nested groupingBy). Design: precomputed
daily totals vs computing on request.
