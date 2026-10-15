package com.mediqo.doctors;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.json.JsonCompareMode;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.empty;
import static org.hamcrest.Matchers.not;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract on the demo directory. */
class DoctorContractTest extends ApiTest {

    @Test
    void bothFiltersInAnyCase() throws Exception {
        mvc.perform(get("/doctors").param("speciality", "cardiology").param("city", "PUNE")).andExpect(status().isOk())
                .andExpect(jsonPath("$[*].name", contains("Dr Asha Mehta", "Dr Fatima Ali")));
    }

    @Test
    void oneFilterOrNone() throws Exception {
        mvc.perform(get("/doctors").param("speciality", "Cardiology"))
                .andExpect(jsonPath("$[*].name", contains("Dr Asha Mehta", "Dr Fatima Ali", "Dr Kabir Khan")));
        mvc.perform(get("/doctors").param("city", "bengaluru"))
                .andExpect(jsonPath("$[*].name", contains("Dr John Dsouza", "Dr Kabir Khan", "Dr Meena Rao")));
        mvc.perform(get("/doctors")).andExpect(jsonPath("$.length()").value(6));
        mvc.perform(get("/doctors").param("speciality", "Neurology")).andExpect(status().isOk()).andExpect(jsonPath("$", empty()));
    }

    @Test
    void oneDoctorAsTheDirectoryShowsThem() throws Exception {
        mvc.perform(get("/doctors/1")).andExpect(status().isOk()).andExpect(content().json("""
                {"id":1,"name":"Dr Asha Mehta","speciality":"Cardiology","city":"Pune","registrationNumber":"MMC-2011-04512",
                 "clinic":"Mediqo Koregaon Park","clinicAddress":"Lane 5, Koregaon Park, Pune 411001"}""", JsonCompareMode.STRICT));
        mvc.perform(get("/doctors")).andExpect(content().string(not(org.hamcrest.Matchers.containsString("90000"))));
    }

    @Test
    void anUnknownDoctorIs404() throws Exception {
        mvc.perform(get("/doctors/99")).andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.title").value("Doctor not found"));
    }

    @Test
    void badFiltersAre400() throws Exception {
        mvc.perform(get("/doctors").param("speciality", "Cardio1ogy")).andExpect(status().isBadRequest());
        mvc.perform(get("/doctors").param("city", "x".repeat(41))).andExpect(status().isBadRequest());
        mvc.perform(get("/doctors/abc")).andExpect(status().isBadRequest());
    }
}
