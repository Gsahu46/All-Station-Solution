# Station 077 plan: Hospital staff roles

**Problem.** Mediqo's ward app hid buttons by role, but every signed-in user could call every endpoint: a receptionist
read clinical notes by typing the URL.

**Endpoints.** HTTP Basic, stateless (in-memory demo staff, bcrypt). `GET /appointments/today` (appointments:read):
reception sees time, patient, doctor; clinicians also the reason. `GET /patients/{id}/notes` (notes:read and in
care: a doctor's own patient, a nurse's ward). `POST /patients/{id}/prescriptions` (prescriptions:write and own
patient) {drug 1-80, doseMg 1-5000, timesPerDay 1-6, days 1-90}: 201 with Location. 401 Basic challenge; 403 for
role or patient; an unknown patient is 403 too (ids cannot be probed); every other path denyAll.

**Security.** Roles are sets of permissions (least privilege): reception {appointments:read}, nurse {+ notes:read},
doctor {+ prescriptions:write}. Two lines: request rules in the filter chain, and @PreAuthorize on each controller
method with `@ward.inCareOf(authentication, #patientId)`.

**Trap.** `UiOnlyRolesTrapTest`: the old menu hid Notes from reception and Prescribe from nurses; calling the API
directly is now 403; the control (a doctor for her patient) works.

**Found while building.** (1) `@ward.inCareOf(...)` in @PreAuthorize failed with SpEL EL1004E "method cannot be
found" while the method was package-private: SpEL calls public methods only. (2) Each line of defence alone hides the
other's removal: dropping a request rule turned no test red, because @PreAuthorize still refused; only the direct
controller call and the per-patient tests show what each line adds. (3) The first 403 text said "your role", which is
wrong for a doctor asking about someone else's patient.

**Mutations.** notes request rule -> authenticated(): 0; prescriptions request rule -> authenticated(): 0 (method
security backs both); no @PreAuthorize on notes -> 5; inCareOf always true -> 5; no nurse-ward rule -> 1; no
@EnableMethodSecurity -> 5; reason shown to everyone -> 1; denyAll -> authenticated() -> 1.

**Review.** One `anyRequest().authenticated()` rule "because @PreAuthorize does the rest", but @EnableMethodSecurity
removed, so every annotation is inert; reason shown to reception: 10 of 16 fail.

**Practice.** 1: audit every notes read, visible to the privacy officer only (audit:read). 2: break-glass for doctors
with X-Emergency-Reason (10-200 characters), recorded as an emergency. 3 (paper): roles from the hospital directory
(LDAP/AD groups), and reviewing access every quarter.
