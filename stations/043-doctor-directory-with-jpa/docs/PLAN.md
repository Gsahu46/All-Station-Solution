# Station 043 plan: Doctor directory with JPA

**Problem.** Mediqo wrote SQL by hand for every doctor search; adding a speciality filter took a week. An earlier
attempt with JPA returned the Doctor entity as JSON.

**Endpoints.** `GET /doctors?speciality&city` (both optional, any case, letters and spaces 2-40) 200 [DoctorView] by
name; `GET /doctors/{id}` 200 DoctorView / 404; 400 bad filter or id.

**Code.** @Entity Doctor (public fields plus personal phone, salary, notes; @ManyToOne LAZY Clinic), @Entity Clinic.
DoctorRepository extends JpaRepository with derived queries (findBySpecialityIgnoreCaseAndCityIgnoreCaseOrderByName
and friends) each with @EntityGraph("clinic"). DoctorDirectory maps to DoctorView inside @Transactional(readOnly).
open-in-view: false; ddl-auto: validate against Flyway.

**Trap.** `EntityAsJsonTrapTest`, with the app's own JsonMapper (Jackson 3) and Hibernate 7, found by a probe while
building: outside a transaction the lazy clinic throws LazyInitializationException ("no session"); inside one (what
open-in-view would do) the JSON has personalPhone, salaryPaise, internalNotes and hibernateLazyInitializer. With
package-private Clinic getters the proxy was written as {"hibernateLazyInitializer":{}} instead; real entities have
public getters, so the station uses them. Mutations: the view gains the phone -> 2 red; no entity graph on the full
list -> 1 (query count 1 vs 3); no transaction on one -> not caught (the graph already loads the clinic).

**Tests.** Trap, `DoctorContractTest`, `DoctorDatabaseTest` (constraints via SQL, rollback, Hibernate statistics: 1
query with the graph, 3 without).

**Practice.** 1: /clinics/{id}/doctors via findByClinicId. 2: /specialities via JPQL projection. Design: when derived
query names stop scaling (Specifications, Querydsl, plain SQL).
