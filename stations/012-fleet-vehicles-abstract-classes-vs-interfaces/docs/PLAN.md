# Station 012 plan: Fleet vehicles: abstract classes vs interfaces

**Problem.** Dakroute's fleet classes form a tree; an EV van subclassing Van inherited an oil change, and a diesel task
added to the fuel parent reached petrol bikes.

**Endpoint.** `GET /fleet/vehicles/{id}/service-plan` → 200 plan (tasks soonest first, nextDueKm, dueInKm, dueSoon),
404, 400. Problem bodies via spring.mvc.problemdetails.enabled.

**Data.** No database. Vehicle record = Powertrain enum + Body enum, both implementing ServiceItems; ServicePlanner
computes next multiple of each interval (Math.ceilDiv), sorts by dueInKm then name.

**Trap.** Deep abstract-class tree. `DeepInheritanceTrapTest`: EV van gets an oil change, petrol bike a diesel filter;
real API does neither. Mutation: body dropped from Vehicle.parts() -> 4 tests red.

**Tests.** Trap, `ServicePlanContractTest`, `ServicePlannerTest` (all 9 combinations).

**Practice.** 1: CNG powertrain + vehicle 6 in two files. 2: withinKm filter (pom-additions: validation starter).
Design: when a template-method abstract class fits.
