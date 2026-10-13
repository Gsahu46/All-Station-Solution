# Station 016 plan: Loan EMI calculator and schedule

**Problem.** Tijori's quote shows an EMI ₹3 off the bank's (an intermediate step rounded to 4 decimals), and the
schedule repeats the rounded EMI every month, so the last month leaves -₹11.91 instead of closing at zero.

**Endpoints.** `POST /loan-quotes` (product, principalPaise ₹10,000..₹1 crore, tenureMonths 6..360) 201 + Location;
400 bad fields; 422 no rate valid today. `GET /loan-quotes/{id}/schedule` rows; 404 unknown id.

**Data.** No database. Quotes in memory. Rates in `application.yaml`, each with a `from` date; the rate on a day is
`TreeMap.floorEntry`. BigDecimal with `MathContext.DECIMAL128` throughout; EMI rounded once, to whole rupees;
interest per month rounded to the paisa; the last month pays what is left. Found while testing every combination:
a small, long loan with an EMI rounded up is repaid early, so a month that clears the balance ends the schedule.

**Trap.** Same EMI every month; rounding an intermediate value. `LastInstalmentTrapTest`: -1,191 paise left;
₹23,766 vs ₹23,769; the real last EMI is 2,376,900 - 1,191. Mutation: no final adjustment and no cap -> 5 tests red.

**Tests.** Trap, `LoanQuoteContractTest`, `EmiTest` (textbook value, 80 combinations close at zero, early close, rate dates).

**Practice.** 1: part-prepayment that keeps the EMI and shortens the loan. 2: disbursal date picks the rate.
Design: reduce EMI or reduce tenure after a prepayment.
