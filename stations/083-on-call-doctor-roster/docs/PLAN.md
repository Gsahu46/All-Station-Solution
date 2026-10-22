# Station 083 plan: On-call doctor roster

**Problem.** Mediqo's night roster: two cardiology doctors pressed "go off call" at the same moment. Each request
counted two doctors on call, each took its doctor off, and the ward had nobody on call.

**Endpoint.** `POST /rosters/{ward}/off-call` {doctor}: 200 with the doctor and how many are still on call; the last
doctor(s) needed for the ward's minimum 409; unknown ward or doctor 404; a name not shaped `dr.name` 400; a doctor
already off: the same 200, nothing changes (safe to repeat); a lost race with no retries left 503.

**Isolation.** The check and the update run in one SERIALIZABLE transaction. PostgreSQL fails one of two
transactions that read each other's rows and wrote different ones (SQLState 40001, usually at commit); the app runs
it again from the start, up to 5 attempts in all, with a short random wait, and then it sees the truth.

**Database.** wards (min on call >= 1), roster (PK ward+doctor, doctor shape), roster_changes (went off/on). The
rule for every writer: constraint trigger `wards_keep_min_on_call`, deferred to commit. Its limit: two READ
COMMITTED commits at the same instant can both pass it; deleting a roster row is not covered.

**Trap.** `WriteSkewTrapTest`: two real JDBC transactions, step by step, trigger disabled (the old schema). READ
COMMITTED: both count two, both go off, 0 on call. SERIALIZABLE: the second commit fails with 40001, 1 on call.

**Found while building.** (1) With READ COMMITTED instead of SERIALIZABLE, the parallel tests still ended with one
doctor on call: the deferred trigger refused the loser at commit. Only the check that a retry happened failed. The
trigger is the net; isolation is what gives the right answer. (2) Removing the 503 mapping changed no test: a test
with 1 attempt was added (`RosterBusyTest`).

**Mutations.** READ COMMITTED -> 1; no retry -> 2; no minimum check -> 1; no trigger -> 3; already-off shortcut
removed -> 2; 503 not mapped -> 1 (after adding RosterBusyTest); no change row -> 3; minimum 0 allowed -> 1.

**Review.** "A serialization failure means the other doctor won": 40001 answered 409 with no retry; the minimum
check moved before the already-off shortcut. 4 of 13 fail.

**Practice.** 1: handover (one on, one off, one transaction). 2: PUT minimum, with a V3 trigger on wards.
3 (paper): the roster across shifts (time ranges, exclusion constraints).
