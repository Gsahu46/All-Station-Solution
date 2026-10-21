# Station 077 · Hospital staff roles

Working Systems · 0–2 years · Core · Healthcare · Types: Security

Spring Boot 4.1.1 · Java 25 · Spring Security 7 · request rules and @PreAuthorize · authorities as permissions · HTTP Basic. Needs JDK 25 (or 21, see Set up & code). No database and no Docker. No Maven install: use `./mvnw` (`.\mvnw.cmd` on Windows).

**Simulation:** Staff, patients, notes and appointments are invented demo data held in memory, not Mediqo's and not real patients. Prescriptions are records in a list: nothing reaches a pharmacy.

Read in three levels: 1 Understand (about 5 minutes, no code), 2 Build, 3 Go deeper. Run `./mvnw test` for all 16 tests.

# 1 · Understand

## The problem in real life

1.  **Buttons hidden, doors open**

    Mediqo's ward app showed each role only its own buttons. The API behind it checked only that someone was signed in.

2.  **A receptionist reads notes**

    A receptionist typed a notes URL she had seen in a link, and the API returned a patient's clinical notes.

3.  **The fix**

    The API itself decides: each endpoint needs a permission, each role has only the permissions its work needs, and each clinical request is also checked against who is in the caller's care.

Hiding a button is a convenience. The check belongs where the data is.

## What are we building?

Three endpoints for ward staff, each guarded twice: a permission rule at the door, and a per-patient rule in the code.

## An everyday analogy

A hospital lift that skips the ICU floor for visitors is not security: the stairs still lead there. The lock is on the ICU door, and the nurse inside still checks who you are visiting.

## How it works in 4 steps

1.  **Sign in**: the staff member's username and password with every request.
2.  **Door**: the filter chain checks the endpoint's permission; unknown paths are refused.
3.  **Bedside**: `@PreAuthorize` checks the permission again and whether this patient is in the caller's care.
4.  **Answer**: only then does the code read or write.

Check yourself: Dr Bose is a doctor. Why can she not read Kavya Menon's notes?

She has the permission, but Kavya is Dr Sharma's patient on Cardiology. The per-patient rule refuses it: `aDoctorCannotReadOrPrescribeForAnotherDoctorsPatient`. A role alone is not enough.

## What this station is not

- **No database.** Demo records live in memory.
- **No sign-in design.** HTTP Basic keeps the focus on authorization; tokens are stations 073 and 074.
- **No row-level filtering in SQL.** That is station 078.

## Key terms

| Term                       | Simple meaning                                                           | Everyday example                                      | In this project                        |
|----------------------------|--------------------------------------------------------------------------|-------------------------------------------------------|----------------------------------------|
| **Role**                   | A job: receptionist, nurse, doctor.                                      | The badge colour at a hospital.                       | `ROLE_NURSE`                           |
| **Authority (permission)** | One thing a role may do.                                                 | "May enter the pharmacy."                             | `notes:read`                           |
| **Least privilege**        | Each role gets only what its work needs.                                 | The cleaner's key opens cupboards, not the drug safe. | reception has `appointments:read` only |
| **Request rule**           | A check in the filter chain on the URL and method, before any code runs. | The guard at the ward door.                           | `requestMatchers(...)`                 |
| **@PreAuthorize**          | A check on a method, in the code, with access to its arguments.          | The nurse at the bedside who checks the wristband.    | `@ward.inCareOf(...)`                  |
| **401 and 403**            | 401: who are you? 403: we know, and you may not.                         | No badge, against the wrong badge.                    | Basic challenge; "Not allowed"         |

# 2 · Build: Spec

## Business problem

**Mediqo** (a fictional hospital): a receptionist could read clinical notes, because every signed-in user could call every endpoint.

## Acceptance criteria

Demo staff: reception.anu; nurse.ritu (Cardiology) and nurse.joseph (Orthopaedics); dr.sharma (patients P-1001, P-1002) and dr.bose (P-2001).

1.  **Given** any staff member, **then** today's appointments; the reason only for nurses and doctors.
2.  **Given** a doctor and her own patient, or a nurse and a patient on her ward, **then** the notes.
3.  **Given** a doctor and her own patient, **then** a prescription is recorded (`201`).
4.  **Given** reception asking for notes, or a nurse prescribing, **then** `403`.
5.  **Given** another doctor's patient, another ward, or an unknown patient, **then** `403`.
6.  **Given** no or wrong credentials, **then** `401`.

## Requirements

- Permissions are checked by the API, in the filter chain and again in the code.
- Roles hold the fewest permissions their work needs.
- Paths without a rule are refused.

## Learning objectives

- Model roles as sets of permissions.
- Write request rules and `@PreAuthorize` rules, and say what each one can see.
- Add a per-record rule (whose patient is this?) next to the role rule.
- Tell 401 from 403, and test both.

# 2 · Build: API contract

## Endpoints

| Method | Path                           | Needs                                                                                            |
|--------|--------------------------------|--------------------------------------------------------------------------------------------------|
| `GET`  | `/appointments/today`          | `appointments:read` (everyone)                                                                   |
| `GET`  | `/patients/{id}/notes`         | `notes:read` (nurses, doctors), and the patient in your care                                     |
| `POST` | `/patients/{id}/prescriptions` | `prescriptions:write` (doctors), and your own patient. Body `{drug, doseMg, timesPerDay, days}`. |

## Status codes

| Status    | When                                                                                                   |
|-----------|--------------------------------------------------------------------------------------------------------|
| 200 / 201 | Read / prescription recorded                                                                           |
| 400       | A prescription field missing or out of range                                                           |
| 401       | No or wrong credentials                                                                                |
| 403       | The role lacks the permission; the patient is not in your care, or does not exist; a path with no rule |

## Captured examples

Captured with curl from the running app on 21 Oct 2026. JSON bodies are indented for reading; `Date`, connection and standard security headers are left out.

### Case 1: a doctor reads her patient's notes

**Why:** permission and care both hold.

Request

``` code
GET /patients/P-1001/notes HTTP/1.1
Authorization: Basic ZHIuc2hhcm1hOnNoYXJtYS1kZW1vLXBhc3M=
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 102

[
  {
    "writtenBy": "dr.sharma",
    "text": "Chest pain on exertion; ECG shows ST changes. Start beta blocker."
  }
]
```

### Case 2: reception tries the same URL

**Why:** `403`: the incident, refused by the API.

Request

``` code
GET /patients/P-1001/notes HTTP/1.1
Authorization: Basic cmVjZXB0aW9uLmFudTphbnUtZGVtby1wYXNz
```

Response

``` code
HTTP/1.1 403 
Content-Type: application/problem+json
Content-Length: 147

{
  "title": "Not allowed",
  "status": 403,
  "detail": "Not allowed for your role, or this patient is not in your care.",
  "instance": "/patients/P-1001/notes"
}
```

### Case 3: reception's view of today

**Why:** who, when, with whom; the reason is clinical, so `null`.

Request

``` code
GET /appointments/today HTTP/1.1
Authorization: Basic cmVjZXB0aW9uLmFudTphbnUtZGVtby1wYXNz
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 160

[
  {
    "time": "09:30:00",
    "patient": "Kavya Menon",
    "doctor": "dr.sharma",
    "reason": null
  },
  {
    "time": "11:00:00",
    "patient": "Lakshmi Pillai",
    "doctor": "dr.bose",
    "reason": null
  }
]
```

### Case 4: a nurse's view of today

**Why:** clinicians see the reason.

Request

``` code
GET /appointments/today HTTP/1.1
Authorization: Basic bnVyc2Uucml0dTpyaXR1LWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 200 
Content-Type: application/json
Content-Length: 187

[
  {
    "time": "09:30:00",
    "patient": "Kavya Menon",
    "doctor": "dr.sharma",
    "reason": "Cardiology follow-up"
  },
  {
    "time": "11:00:00",
    "patient": "Lakshmi Pillai",
    "doctor": "dr.bose",
    "reason": "Wound check"
  }
]
```

### Case 5: a nurse asks about another ward's patient

**Why:** right role, wrong patient: `403`.

Request

``` code
GET /patients/P-1001/notes HTTP/1.1
Authorization: Basic bnVyc2Uuam9zZXBoOmpvc2VwaC1kZW1vLXBhc3M=
```

Response

``` code
HTTP/1.1 403 
Content-Type: application/problem+json
Content-Length: 147

{
  "title": "Not allowed",
  "status": 403,
  "detail": "Not allowed for your role, or this patient is not in your care.",
  "instance": "/patients/P-1001/notes"
}
```

### Case 6: a doctor prescribes for her patient

**Why:** `201` with a Location.

Request

``` code
POST /patients/P-2001/prescriptions HTTP/1.1
Authorization: Basic ZHIuYm9zZTpib3NlLWRlbW8tcGFzcw==
Content-Type: application/json

{
  "drug": "Paracetamol",
  "doseMg": 500,
  "timesPerDay": 3,
  "days": 5
}
```

Response

``` code
HTTP/1.1 201 
Location: /patients/P-2001/prescriptions/RX-d6ac7bfd
Content-Type: application/json

{
  "id": "RX-d6ac7bfd",
  "patientId": "P-2001",
  "drug": "Paracetamol",
  "doseMg": 500,
  "timesPerDay": 3,
  "days": 5,
  "prescribedBy": "dr.bose"
}
```

### Case 7: a nurse tries to prescribe

**Why:** no `prescriptions:write`: `403`.

Request

``` code
POST /patients/P-2001/prescriptions HTTP/1.1
Authorization: Basic bnVyc2Uuam9zZXBoOmpvc2VwaC1kZW1vLXBhc3M=
Content-Type: application/json

{
  "drug": "Paracetamol",
  "doseMg": 500,
  "timesPerDay": 3,
  "days": 5
}
```

Response

``` code
HTTP/1.1 403 
Content-Type: application/problem+json
Content-Length: 155

{
  "title": "Not allowed",
  "status": 403,
  "detail": "Not allowed for your role, or this patient is not in your care.",
  "instance": "/patients/P-2001/prescriptions"
}
```

### Case 8: a doctor asks about another doctor's patient

**Why:** `403`.

Request

``` code
GET /patients/P-1001/notes HTTP/1.1
Authorization: Basic ZHIuYm9zZTpib3NlLWRlbW8tcGFzcw==
```

Response

``` code
HTTP/1.1 403 
Content-Type: application/problem+json
Content-Length: 147

{
  "title": "Not allowed",
  "status": 403,
  "detail": "Not allowed for your role, or this patient is not in your care.",
  "instance": "/patients/P-1001/notes"
}
```

### Case 9: no credentials

**Why:** `401` with a Basic challenge.

Request

``` code
GET /patients/P-1001/notes HTTP/1.1
```

Response

``` code
HTTP/1.1 401 
WWW-Authenticate: Basic realm="mediqo"
Content-Type: application/problem+json
Content-Length: 130

{
  "title": "Sign-in required",
  "status": 401,
  "detail": "Send a valid staff username and password.",
  "instance": "/patients/P-1001/notes"
}
```

# 2 · Build: Edge cases & trap

## Edge cases

| Case                                                | What happens                       | Proved by                                                     |
|-----------------------------------------------------|------------------------------------|---------------------------------------------------------------|
| Own patient's notes                                 | `200`                              | `aDoctorReadsTheirPatientsNotes`                              |
| A nurse, her ward                                   | `200`                              | `aNurseReadsNotesOfPatientsOnTheirWard`                       |
| A doctor prescribes                                 | `201`, Location, drug name trimmed | `aDoctorPrescribesForTheirPatient`                            |
| Today's list by role                                | Reason for clinicians only         | `everyoneSeesTodaysAppointmentsButOnlyCliniciansSeeTheReason` |
| Bad prescriptions                                   | `400`                              | `aBadPrescriptionIs400`                                       |
| Unknown patient                                     | `403`, like someone else's         | `anUnknownPatientIsAnsweredLikeSomeoneElsesPatient`           |
| No, wrong or unknown credentials                    | `401`                              | `noOrWrongCredentialsAre401`                                  |
| Another doctor's patient                            | `403` to read and to prescribe     | `aDoctorCannotReadOrPrescribeForAnotherDoctorsPatient`        |
| Another ward                                        | `403`                              | `aNurseCannotReadNotesFromAnotherWard`                        |
| The controller called with no request rule in front | Still refused by `@PreAuthorize`   | `theCodeRefusesEvenIfARequestRuleIsMissing`                   |
| Paths and methods with no rule                      | `403`                              | `pathsWithoutARuleAreRefused`                                 |
| Odd patient ids                                     | `400` or `403`, never an error     | `oddPatientIdsAre403Or400NeverAnError`                        |

## The trap

Plausible but wrong

Checking roles only in the UI, while every endpoint stays open.

- **Reception and notes.** The old menu has no Notes button for reception. The URL still exists; the API now answers `403`.
- **A nurse and prescriptions.** No Prescribe button for nurses; the API now answers `403`.
- **Reception and prescriptions.** `403`.
- **The control.** Dr Sharma, for her own patient: notes and a prescription work.

While building, each part was undone once. Dropping a request rule (notes or prescriptions) turned 0 tests red: `@PreAuthorize` still refused. Dropping `@PreAuthorize` on notes turned 5 red, an always-true care rule 5, no nurse-ward rule 1, no `@EnableMethodSecurity` 5, the reason shown to everyone 1, and `denyAll` replaced by `authenticated` 1.

``` code
package com.mediqo.wards;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. In the old system the roles lived in the ward app's menu: reception never saw a "Notes" button. The
 * API behind it let every signed-in user call every endpoint. Each test shows what the old menu hid, then calls the
 * endpoint directly, as anyone with the URL can.
 */
class UiOnlyRolesTrapTest extends ApiTest {

    /** The old ward app's menu, as it was: the only place roles were checked. */
    static List<String> oldMenu(String role) {
        return switch (role) {
            case "RECEPTIONIST" -> List.of("Appointments");
            case "NURSE" -> List.of("Appointments", "Notes");
            default -> List.of("Appointments", "Notes", "Prescribe");
        };
    }

    @Test
    void receptionCouldReadClinicalNotesByCallingTheApi() throws Exception {
        assertThat(oldMenu("RECEPTIONIST")).doesNotContain("Notes");   // hidden on screen
        notes("reception.anu", "P-1001").andExpect(status().isForbidden());   // and now refused by the API
    }

    @Test
    void aNurseCouldPrescribeByCallingTheApi() throws Exception {
        assertThat(oldMenu("NURSE")).doesNotContain("Prescribe");
        prescribe("nurse.ritu", "P-1001", ASPIRIN).andExpect(status().isForbidden());
    }

    @Test
    void receptionCouldPrescribeToo() throws Exception {
        prescribe("reception.anu", "P-1001", ASPIRIN).andExpect(status().isForbidden());
    }

    @Test
    void theRightRoleForTheRightPatientWorks() throws Exception {
        // The control: a doctor, for her own patient.
        notes("dr.sharma", "P-1001").andExpect(status().isOk());
        prescribe("dr.sharma", "P-1001", ASPIRIN).andExpect(status().isCreated());
    }
}
```

# 2 · Build: Set up & code

## Set up and run

| You need | Version                                         | Check with      |
|----------|-------------------------------------------------|-----------------|
| JDK      | 25 (recommended). JDK 21 also works, see below  | `java -version` |
| Docker   | Not needed                                      |                 |
| Maven    | Not needed: the project ships the Maven wrapper |                 |

**macOS / Linux**

``` code
./mvnw spring-boot:run      # the API on http://localhost:8080
./mvnw test                 # all 16 tests
```

**Windows (PowerShell)**

``` code
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

On JDK 21, add `-Djava.version=21`. Nothing here needs a Java 25 feature.

## Try it yourself

The same URL, three people:

``` code
for who in dr.sharma:sharma-demo-pass nurse.joseph:joseph-demo-pass reception.anu:anu-demo-pass; do
  curl -s -o /dev/null -w "${who%%:*} %{http_code}\n" -u "$who" http://localhost:8080/patients/P-1001/notes
done
```

It prints `dr.sharma 200`, `nurse.joseph 403` (another ward) and `reception.anu 403`.

## Troubleshooting

| You see                                                      | Cause                                                  | Fix                                                                                                                |
|--------------------------------------------------------------|--------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|
| `EL1004E: Method call: Method inCareOf(...) cannot be found` | The bean method used in `@PreAuthorize` is not public. | Make it public. Found while building this station.                                                                 |
| `@PreAuthorize` seems to do nothing                          | Method security is not switched on.                    | Add `@EnableMethodSecurity`: without it the annotations are ignored, silently.                                     |
| `403` on a new endpoint                                      | `denyAll()` at the end of the chain.                   | Add a request rule and a `@PreAuthorize`, on purpose.                                                              |
| `#patientId` is null in the rule                             | Parameter names were not compiled in.                  | Spring Boot's Maven parent compiles with `-parameters`; keep it, or name the parameter in the expression's source. |

## Project layout

``` tree
stations/077-hospital-staff-roles/
├── pom.xml, mvnw, mvnw.cmd, .mvn/
├── src/main/java/com/mediqo/wards/
│   ├── SecurityConfig.java   ├── WardController.java   ├── Ward.java
│   ├── ProblemResponses.java   └── WardsApplication.java
├── src/main/resources/application.yaml
├── src/test/java/com/mediqo/wards/   (see Tests)
├── challenge/                Practice tests; solutions ship separately
├── review/                   The flawed version (see Review)
└── docs/                     capture script, captures, saved runs
```

## Code walkthrough

In the order a request travels.

#### `src/main/java/com/mediqo/wards/SecurityConfig.java`

Does  
The door: one permission per endpoint, the staff and their roles.

Why  
Request rules by method and path; everything else refused; `@EnableMethodSecurity` switches on the second line.

Without it  
A new endpoint open to every signed-in user, or a role with more than its work needs.

- Removing one request rule turned no test red, because `@PreAuthorize` still refused. Two lines of defence hide each other's gaps; only tests that bypass one line (calling the controller directly) show what the other adds. Found while building.
- CSRF is off: credentials travel in a header with every request, never in a cookie a browser adds by itself.

#### `src/main/java/com/mediqo/wards/WardController.java`

Does  
The bedside: each method's rule, next to the code it protects.

Why  
`@PreAuthorize` repeats the permission and adds the per-patient rule; reception's view of the day leaves out the reason.

Without it  
A forgotten request rule exposing notes, or a doctor reading any patient's notes.

#### `src/main/java/com/mediqo/wards/Ward.java`

Does  
The demo records, and the care rule.

Why  
`inCareOf`: a doctor's own patients, a nurse's ward; an unknown patient is not in anyone's care.

Without it  
Probing patient ids by watching 403 against 404.

`inCareOf` must be `public`: SpEL in `@PreAuthorize` calls public methods only, and otherwise fails with EL1004E "method cannot be found". Found while building.

#### `src/main/java/com/mediqo/wards/ProblemResponses.java`

401 with a Basic challenge and 403 in the same problem JSON as every other error.

#### `src/main/resources/application.yaml`

Problem details on; nothing else to configure.

#### `src/main/java/com/mediqo/wards/WardsApplication.java`

Entry point.

# 2 · Build: Tests

## Required tests for this station

| Required by   | Requirement                                                       | Test class                | Result |
|---------------|-------------------------------------------------------------------|---------------------------|--------|
| Every station | HTTP contract: valid, invalid, not found                          | `WardContractTest` (6)    | pass   |
| Every station | Reproduce the failure before the fix                              | `UiOnlyRolesTrapTest` (4) | pass   |
| Security      | 401, 403, one user accessing another user's data, malicious input | `WardSecurityTest` (6)    | pass   |

"Not found" here is the unknown patient, answered like someone else's on purpose. "Another user's data": another doctor's patient and another ward's patient.

## Run output

JDK 25.0.1, Spring Boot 4.1.1, Spring Security 7.1. No Docker. Nothing skipped. Saved in `docs/test-run.txt`.

``` console
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.wards.UiOnlyRolesTrapTest
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.wards.WardContractTest
[INFO] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0 -- in com.mediqo.wards.WardSecurityTest
[INFO] Tests run: 16, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

## Test files

#### `src/test/java/com/mediqo/wards/UiOnlyRolesTrapTest.java`

Written first: what the old menu hid, and the same calls made directly.

#### `src/test/java/com/mediqo/wards/WardSecurityTest.java`

401, other patients and wards, the code's own refusal without a request rule, paths with no rule, odd ids.

#### `src/test/java/com/mediqo/wards/WardContractTest.java`

Notes, prescriptions and appointments through HTTP.

#### `src/test/java/com/mediqo/wards/ApiTest.java`

Shared setup: request helpers with HTTP Basic.

# 2 · Build: Practice

## How to do a challenge

1.  Copy the challenge test from `challenge/` into `src/test/java/com/mediqo/wards/`.
2.  Run it and watch it fail: `./mvnw test -Dtest=NotesAuditChallengeTest`.
3.  Change the code until it passes, then run `./mvnw test` to check the other 16 tests.

Checked (`docs/challenge-run.txt`): with the reference solutions copied in, all 20 tests pass (16 station tests and 4 challenge tests).

Challenge 1 · Beginner-friendly · about 25 minutes

## Who read which notes

Record every read of clinical notes (staff, patient). `GET /audit/notes-reads` lists them for the privacy officer `admin.meena` (permission `audit:read`) only.

**Done when:** both tests in `NotesAuditChallengeTest` pass.

Hints

- A new permission and a new user; a request rule and a `@PreAuthorize` for the new path.
- Record inside the notes method, after the rule has passed.

#### `challenge/NotesAuditChallengeTest.java`

``` code
package com.mediqo.wards;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.hasItem;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: every read of clinical notes is recorded (staff, patient). GET /audit/notes-reads lists them for the
 * privacy officer admin.meena (password "meena-demo-pass", permission audit:read) only; clinicians get 403.
 */
class NotesAuditChallengeTest extends ApiTest {

    @Test
    void thePrivacyOfficerSeesWhoReadWhichNotes() throws Exception {
        notes("dr.sharma", "P-1002").andExpect(status().isOk());
        mvc.perform(get("/audit/notes-reads").with(httpBasic("admin.meena", "meena-demo-pass"))).andExpect(status().isOk())
                .andExpect(jsonPath("$[*].staff", hasItem("dr.sharma"))).andExpect(jsonPath("$[*].patientId", hasItem("P-1002")));
    }

    @Test
    void cliniciansCannotReadTheAudit() throws Exception {
        mvc.perform(get("/audit/notes-reads").with(httpBasic("dr.sharma", "sharma-demo-pass"))).andExpect(status().isForbidden());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 2 · Go deeper · about 35 minutes

## Break-glass for emergencies

A doctor may read the notes of a patient not in their care by sending `X-Emergency-Reason` (10 to 200 characters); the audit marks it as an emergency, with the reason. Nurses cannot, and a short reason does not count.

**Done when:** both tests in `BreakGlassChallengeTest` pass (after challenge 1).

Hints

- Add `or @ward.breakGlass(authentication)` to the rule; the bean can read the header from `RequestContextHolder`.
- Keep the controller method's signature: a test calls it directly.

#### `challenge/BreakGlassChallengeTest.java`

``` code
package com.mediqo.wards;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.hasItem;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: break-glass. In an emergency a doctor may read the notes of a patient not in their care by sending
 * X-Emergency-Reason (10 to 200 characters). It works, and the audit marks it as an emergency with the reason.
 * Nurses cannot break the glass, and a reason that is too short does not count. Needs challenge 1's audit.
 */
class BreakGlassChallengeTest extends ApiTest {

    @Test
    void aDoctorCanBreakTheGlassAndItIsRecorded() throws Exception {
        mvc.perform(get("/patients/P-1001/notes").header("X-Emergency-Reason", "Collapsed in A&E, own doctor off duty")
                .with(httpBasic("dr.bose", "bose-demo-pass"))).andExpect(status().isOk());
        mvc.perform(get("/audit/notes-reads").with(httpBasic("admin.meena", "meena-demo-pass")))
                .andExpect(jsonPath("$[?(@.staff == 'dr.bose' && @.emergency == true)].reason", hasItem("Collapsed in A&E, own doctor off duty")));
    }

    @Test
    void nursesCannotAndAShortReasonDoesNotCount() throws Exception {
        mvc.perform(get("/patients/P-2001/notes").header("X-Emergency-Reason", "Collapsed in the corridor outside")
                .with(httpBasic("nurse.ritu", "ritu-demo-pass"))).andExpect(status().isForbidden());
        mvc.perform(get("/patients/P-1001/notes").header("X-Emergency-Reason", "urgent")
                .with(httpBasic("dr.bose", "bose-demo-pass"))).andExpect(status().isForbidden());
    }
}
```

*Solution: in the separate solutions pack. Try first.*

Challenge 3 · design on paper, no code

## Roles from the hospital directory

Staff join, move wards and leave every week. Design how roles and wards come from the hospital's directory (groups in Active Directory or another LDAP server) instead of code, how fast a removal takes effect, and how a quarterly access review would find a nurse who still reads notes on a ward she left.

# 3 · Go deeper: Design

## Implementation approach

1.  Write the trap test: what the menu hid, called directly.
2.  Turn roles into sets of permissions.
3.  One request rule per endpoint; `denyAll` for the rest.
4.  `@PreAuthorize` on each method, with the per-patient rule.

## Design alternatives and trade-offs

| Approach                                                  | What it costs                                     | Verdict                          |
|-----------------------------------------------------------|---------------------------------------------------|----------------------------------|
| Permissions per role, request rules plus @PreAuthorize    | Rules in two places to keep in step.              | Chosen                           |
| Roles checked in the UI only                              | Anyone with a URL gets everything.                | The trap                         |
| Request rules only                                        | Cannot see whose record it is.                    | Not enough for per-patient rules |
| @PreAuthorize only                                        | A method without the annotation is open.          | One forgotten line away          |
| A policy engine (OPA, Cedar) or relationship-based access | Another system; rules out of code, easy to audit. | At scale; see station 079        |

## Database design

No database in this station: the demo records are in memory. In a real system, "in care of" comes from the care-team and ward-assignment tables, and station 078 shows how to put such a rule into the query itself.

# 3 · Go deeper: Production

Audit  
Health data access is usually audited by law: who read which record, when. Challenge 1 builds the start of it.

Emergencies  
A rule that blocks a doctor in A&E costs more than it saves: break-glass with a recorded reason (challenge 2), reviewed afterwards.

Directory  
Roles and wards belong in the hospital's directory, not in code; removals must take effect within minutes.

Logs  
Never log note text or prescription bodies.

# 3 · Go deeper: Interview

## Interview takeaways

Role or authority?

A role is a job; an authority is one permission. Check authorities in code, and map roles to them, so a new role does not mean editing every rule.

Request rules or @PreAuthorize?

Request rules guard paths before any code runs; @PreAuthorize sees the method's arguments and can check the record. Use both: the first as a default, the second for per-record rules.

Why answer 403 for an unknown patient?

So nobody can tell which ids exist by comparing answers. The same reason sign-in gives one answer for unknown users and wrong passwords.

What does @EnableMethodSecurity do?

It switches method security on. Without it, @PreAuthorize annotations are ignored, silently.

What is least privilege?

Each role gets only the permissions its work needs, so a stolen or misused account can do as little as possible.

## Self-check rubric

| Area        | Meets the bar              | Above the bar                                                          |
|-------------|----------------------------|------------------------------------------------------------------------|
| Correctness | All 16 tests pass.         | You ran the flawed version and explained each failure.                 |
| Roles       | Permissions per role.      | Least privilege, down to the fields reception sees.                    |
| Rules       | Request rules and denyAll. | @PreAuthorize with a per-record rule, tested without the request rule. |
| Privacy     | No notes for reception.    | Unknown and someone else's patient look the same.                      |

# 3 · Go deeper: Review

## The pull request

A teammate removes "duplicated" security: the request rules go, since the controller already has `@PreAuthorize`, and the chain becomes one `authenticated()` rule. Reception also asked to see why patients come. Read the two files and list every problem before opening the findings.

#### `review/SecurityConfig.java`

``` code
package com.mediqo.wards;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;

/** One rule for the chain: staff only. The role rules live once, in @PreAuthorize on the controller, not twice. */
@Configuration
class SecurityConfig {

    @Bean
    SecurityFilterChain api(HttpSecurity http, ProblemResponses problems) throws Exception {
        http.authorizeHttpRequests(a -> a
                        .requestMatchers("/error").permitAll()
                        .anyRequest().authenticated())   // every endpoint is for staff; @PreAuthorize on the controller does the rest
                .httpBasic(b -> b.authenticationEntryPoint(problems::unauthenticated))
                .exceptionHandling(x -> x.authenticationEntryPoint(problems::unauthenticated).accessDeniedHandler(problems::forbidden))
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .csrf(csrf -> csrf.disable());   // credentials come in a header with every request, no cookie a browser sends by itself
        return http.build();
    }

    @Bean
    PasswordEncoder passwordEncoder() {
        return PasswordEncoderFactories.createDelegatingPasswordEncoder();
    }

    /**
     * Demo staff. Each role is a set of permissions, least privilege first: reception books, nurses read notes,
     * doctors also prescribe.
     */
    @Bean
    UserDetailsService staff(PasswordEncoder encoder) {
        String[] reception = {"ROLE_RECEPTIONIST", "appointments:read"};
        String[] nurse = {"ROLE_NURSE", "appointments:read", "notes:read"};
        String[] doctor = {"ROLE_DOCTOR", "appointments:read", "notes:read", "prescriptions:write"};
        return new InMemoryUserDetailsManager(
                User.withUsername("reception.anu").password(encoder.encode("anu-demo-pass")).authorities(reception).build(),
                User.withUsername("nurse.ritu").password(encoder.encode("ritu-demo-pass")).authorities(nurse).build(),
                User.withUsername("nurse.joseph").password(encoder.encode("joseph-demo-pass")).authorities(nurse).build(),
                User.withUsername("dr.sharma").password(encoder.encode("sharma-demo-pass")).authorities(doctor).build(),
                User.withUsername("dr.bose").password(encoder.encode("bose-demo-pass")).authorities(doctor).build());
    }
}
```

#### `review/WardController.java`

``` code
package com.mediqo.wards;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.time.LocalTime;
import java.util.List;
import java.util.UUID;

@RestController
class WardController {

    record NewPrescription(@NotBlank @Size(max = 80) String drug, @Min(1) @Max(5000) int doseMg,
                           @Min(1) @Max(6) int timesPerDay, @Min(1) @Max(90) int days) {
    }

    /** One appointment on today's list. */
    record Slot(LocalTime time, String patient, String doctor, String reason) {
    }

    private final Ward ward;

    WardController(Ward ward) {
        this.ward = ward;
    }

    @GetMapping("/appointments/today")
    @PreAuthorize("hasAuthority('appointments:read')")
    List<Slot> today(Authentication staff) {
        // Reception asked to see why each patient is coming, to plan the waiting room.
        return ward.today.stream().map(a -> new Slot(a.time(), a.patientName(), a.doctor(), a.reason())).toList();
    }

    @GetMapping("/patients/{patientId}/notes")
    @PreAuthorize("hasAuthority('notes:read') and @ward.inCareOf(authentication, #patientId)")
    List<Ward.Note> notes(@PathVariable String patientId) {
        return ward.notes.get(patientId);
    }

    @PostMapping("/patients/{patientId}/prescriptions")
    @PreAuthorize("hasAuthority('prescriptions:write') and @ward.inCareOf(authentication, #patientId)")
    ResponseEntity<Ward.Prescription> prescribe(@PathVariable String patientId, @Valid @RequestBody NewPrescription body, Authentication doctor) {
        Ward.Prescription rx = new Ward.Prescription("RX-" + UUID.randomUUID().toString().substring(0, 8), patientId,
                body.drug().strip(), body.doseMg(), body.timesPerDay(), body.days(), doctor.getName());
        ward.prescriptions.add(rx);
        return ResponseEntity.created(URI.create("/patients/" + patientId + "/prescriptions/" + rx.id())).body(rx);
    }
}
```

## Findings

1Method security switched off

"@PreAuthorize does the rest", but `@EnableMethodSecurity` was removed with the duplicate rules. Every annotation in the controller is now ignored, and the only rule left is "signed in": the original incident, with annotations that look like protection.

**Test evidence:** `receptionCouldReadClinicalNotesByCallingTheApi`, `aNurseCouldPrescribeByCallingTheApi`, `receptionCouldPrescribeToo`, `aDoctorCannotReadOrPrescribeForAnotherDoctorsPatient`, `aNurseCannotReadNotesFromAnotherWard`, `theCodeRefusesEvenIfARequestRuleIsMissing`, `anUnknownPatientIsAnsweredLikeSomeoneElsesPatient` and `oddPatientIdsAre403Or400NeverAnError` fail.

2authenticated() instead of denyAll

Paths nobody wrote a rule for are now open to every member of staff.

**Test evidence:** `pathsWithoutARuleAreRefused` fails.

3The reason shown to reception

Why a patient comes is clinical information; planning the waiting room needs the time and the doctor.

**Test evidence:** `everyoneSeesTodaysAppointmentsButOnlyCliniciansSeeTheReason` fails.

## Same tests, flawed version

From `docs/review-run.txt`: the two flawed files copied over the real ones, then the full suite run.

| Test class            | Fixed version | Flawed version |
|-----------------------|---------------|----------------|
| `UiOnlyRolesTrapTest` | 4 / 4         | 1 / 4          |
| `WardContractTest`    | 6 / 6         | 4 / 6          |
| `WardSecurityTest`    | 6 / 6         | 1 / 6          |

The controller still reads as if it were protected. Nothing in a code review of that file alone shows the annotations are dead.
