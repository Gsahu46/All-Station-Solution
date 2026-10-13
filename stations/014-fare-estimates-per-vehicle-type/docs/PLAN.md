# Station 014 plan: Fare estimates per vehicle type

**Problem.** Rydo prices vehicles in one if-else with shared defaults; adding CAB_XL raised auto fares. The old app
also sent its own distance.

**Endpoint.** `GET /fare-estimates?pickup=lat,lng&drop=lat,lng` → 200 distance (server-side, 0.1 km) + farePaise per
vehicle; 400 malformed/missing; 422 outside service area. Extra distance/fare params ignored.

**Data.** No database. FareRule interface (strategy) with PerKmRule and MeterRule records; VehicleType enum holds a
rule; BigDecimal from strings, HALF_UP to whole rupees, paise out. Haversine x 1.3 road factor (demo).

**Trap.** If-else chain with shared defaults. `IfElseChainTrapTest`: auto 10 km Rs 190 instead of 150; real rules keep
150. Mutation: meter extra-km floor removed -> 2 tests red.

**Tests.** Trap, `FareEstimateContractTest` (looks fares up by vehicle name, open to new types), `FareRulesTest`.

**Practice.** 1: EV_CAB in one line. 2: airport toll for cars. Design: night fare and surge as decorators.
