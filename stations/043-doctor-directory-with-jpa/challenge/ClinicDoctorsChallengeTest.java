package com.mediqo.doctors;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /clinics/{id}/doctors lists a clinic's doctors by name, as DoctorView. A derived query can follow
 * the link to the clinic: findByClinicId… An unknown clinic is 404, not an empty list.
 */
class ClinicDoctorsChallengeTest extends ApiTest {

    @Test
    void aClinicListsItsDoctors() throws Exception {
        mvc.perform(get("/clinics/2/doctors")).andExpect(status().isOk())
                .andExpect(jsonPath("$[*].name", contains("Dr John Dsouza", "Dr Kabir Khan", "Dr Meena Rao")))
                .andExpect(jsonPath("$[0].clinic").value("Mediqo Indiranagar"));
    }

    @Test
    void anUnknownClinicIs404() throws Exception {
        mvc.perform(get("/clinics/9/doctors")).andExpect(status().isNotFound());
    }
}
