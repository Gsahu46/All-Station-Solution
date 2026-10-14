# Station 017 plan: GST on invoices

**Problem.** Billora's invoices charge IGST at a hard-coded 18% on every line, even to buyers in its own state, and
round tax line by line, so totals differ from the CA's rate-wise numbers.

**Endpoint.** `POST /invoices/tax-preview` (invoiceDate, placeOfSupply as the 2-digit GST state code, 1-100 lines with
4-digit HSN, quantity, unitPricePaise) 200 with lines, a rate-wise tax summary and totals; 400 bad fields or unknown
state code; 422 no rate for an HSN on that date, naming the line. Nothing is stored.

**Data.** No database. `GstState` enum with code and name. Rates in `application.yaml` by HSN, as dated sets of price
slabs: `TreeMap.floorEntry` by date, then by unit price. Tax per rate group on the summed taxable value, rounded once;
same state: CGST = SGST = half the rate each; other state: IGST.

**Trap.** `WrongTaxTrapTest`: the old code's Rs 863.01 on the office invoice; per-line rounding at the right rates gives
55,144 paise against the CA's 55,142; the fixed preview gives CGST 27,571 + SGST 27,571. Mutations: always IGST -> 2 red;
ignoring the date -> 4 red.

**Tests.** Trap, `TaxPreviewContractTest`, `GstRatesTest` (slab and date boundaries, 1,000 generated invoices within
half a paisa per head).

**Practice.** 1: line discounts (slab after the discount). 2: union territory seller, CGST + UTGST.
Design: e-invoice rounding to the rupee and a round-off line.
