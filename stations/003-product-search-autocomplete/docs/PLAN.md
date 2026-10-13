# Station 003 plan: Product search autocomplete

**Problem.** Kartwala's suggestions scan 2 lakh names with contains() per keystroke: slow, mid-word matches, no ranking.

**Endpoint.** `GET /suggestions?prefix&limit` → 200 (normalised prefix + items, empty allowed), 400 missing/short/long
prefix or limit outside 1-10.

**Data.** No database. 26 products; a TreeMap keyed by each word start (+ \0 + id), built at start-up.

**Trap.** contains() scan. `ContainsScanTrapTest`: naive suggests Balsamic Vinegar for "sam"; index ranks word starts;
on 2 lakh generated products the scan reads 200,026 names, the index 5 entries.
Mutation: indexing every character position -> 2 tests red.

**Tests.** `ContainsScanTrapTest`, `SuggestionContractTest`, `SuggestionIndexTest` (plain unit, Turkish locale).

**Practice.** 1: punctuation as spaces in normalise. 2: out-of-stock filter before the limit, inStock in the response.
Design: precomputed top-N for 1-2 letter prefixes.
