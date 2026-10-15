# Station 041 plan: Clinic appointments report with joins

**Problem.** Mediqo's weekly doctor-load report used an INNER JOIN, so a doctor with no appointments vanished, and it
joined follow-ups row by row, so an appointment with two follow-ups counted twice.

**Endpoint.** `GET /reports/doctor-load?from&to[&minAppointments]` (ISO dates, both included, India days, at most 92
days) 200 {from, to, doctors[{doctorId, name, speciality, appointments, completed, noShows, followUps,
revenuePaise}]} busiest first; 400 to before from, too long, missing or malformed date, negative minimum. An empty
range is 200 with every active doctor at zero.

**SQL.** doctors LEFT JOIN appointments with date and status conditions in ON; follow-ups pre-counted per
appointment in a subquery; count(a.id) and FILTER; coalesce(sum, 0); WHERE d.active; HAVING count(a.id) >= :min.

**Data.** V1 doctors, appointments (FK, status check, fee >= 0, index doctor+time), follow_ups (FK). V2 demo week
5-11 Oct 2026: Mehta 3 (+1 cancelled, 3 follow-ups), Iyer 2 (one at 23:30 Sunday), Rao 1 (+1 at 00:15 Monday),
Khan 0, Das retired.

**Trap.** `InnerJoinTrapTest`: old SQL hides Khan and gives Mehta 4; LEFT JOIN with the date in WHERE hides Khan
again; LEFT JOIN with count(*) gives Khan 1; the report gives 3, 2, 1, 0. Mutations: inner join -> 5 red; conditions
out of ON -> 5; date also in WHERE -> 5; count(*) -> 4; follow-ups row by row -> 2; no coalesce -> 5 errors; retired
doctors -> 3.

**Practice.** 1: noShowPercent with NULLIF. 2: speciality summary with count(DISTINCT). Design: a report over a year
of data for 200 clinics.
