package com.mediqo.reports;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.json.JsonCompareMode;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract on the demo week. */
class DoctorLoadContractTest extends ApiTest {

    @Test
    void theWeekShowsEveryActiveDoctorBusiestFirst() throws Exception {
        mvc.perform(get("/reports/doctor-load").param("from", FROM).param("to", TO)).andExpect(status().isOk())
                .andExpect(content().json("""
                        {"from":"2026-10-05","to":"2026-10-11","doctors":[
                          {"doctorId":1,"name":"Dr Mehta","speciality":"Cardiology","appointments":3,"completed":2,"noShows":1,"followUps":3,"revenuePaise":160000},
                          {"doctorId":2,"name":"Dr Iyer","speciality":"Dermatology","appointments":2,"completed":1,"noShows":0,"followUps":0,"revenuePaise":60000},
                          {"doctorId":3,"name":"Dr Rao","speciality":"Paediatrics","appointments":1,"completed":1,"noShows":0,"followUps":0,"revenuePaise":50000},
                          {"doctorId":4,"name":"Dr Khan","speciality":"Orthopaedics","appointments":0,"completed":0,"noShows":0,"followUps":0,"revenuePaise":0}]}""",
                        JsonCompareMode.LENIENT));   // every listed value checked; new fields may be added
    }

    @Test
    void minAppointmentsFiltersAfterCounting() throws Exception {
        mvc.perform(get("/reports/doctor-load").param("from", FROM).param("to", TO).param("minAppointments", "2"))
                .andExpect(jsonPath("$.doctors[*].name", contains("Dr Mehta", "Dr Iyer")));
    }

    @Test
    void theDaysAreIndiaDaysWithBothEndsIncluded() throws Exception {
        // Dr Iyer's Sunday 23:30 appointment is in; Dr Rao's Monday 00:15 one is not.
        mvc.perform(get("/reports/doctor-load").param("from", "2026-10-11").param("to", "2026-10-11"))
                .andExpect(jsonPath("$.doctors[?(@.name == 'Dr Iyer')].appointments", contains(1)))
                .andExpect(jsonPath("$.doctors[?(@.name == 'Dr Rao')].appointments", contains(0)));
    }

    @Test
    void aWeekWithNoAppointmentsListsEveryoneAtZero() throws Exception {
        mvc.perform(get("/reports/doctor-load").param("from", "2026-01-05").param("to", "2026-01-11"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.doctors.length()").value(4))
                .andExpect(jsonPath("$.doctors[*].revenuePaise", contains(0, 0, 0, 0)));
    }

    @Test
    void badRangesAre400() throws Exception {
        mvc.perform(get("/reports/doctor-load").param("from", TO).param("to", FROM)).andExpect(status().isBadRequest())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
        mvc.perform(get("/reports/doctor-load").param("from", "2026-01-01").param("to", "2026-12-31")).andExpect(status().isBadRequest());
        mvc.perform(get("/reports/doctor-load").param("from", FROM)).andExpect(status().isBadRequest());
        mvc.perform(get("/reports/doctor-load").param("from", "05-10-2026").param("to", TO)).andExpect(status().isBadRequest());
        mvc.perform(get("/reports/doctor-load").param("from", FROM).param("to", TO).param("minAppointments", "-1")).andExpect(status().isBadRequest());
    }
}
