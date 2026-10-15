package com.mediqo.reports;

import org.junit.jupiter.api.Test;
import org.springframework.test.json.JsonCompareMode;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /reports/speciality-load?from&to: per speciality, how many active doctors and how many
 * appointments, busiest first, every speciality with an active doctor included. Counting doctors after joining
 * appointments repeats each doctor once per appointment: count each doctor once.
 */
class SpecialityLoadChallengeTest extends ApiTest {

    @Test
    void eachSpecialityCountsItsDoctorsOnce() throws Exception {
        mvc.perform(get("/reports/speciality-load").param("from", FROM).param("to", TO)).andExpect(status().isOk())
                .andExpect(content().json("""
                        [{"speciality":"Cardiology","doctors":1,"appointments":3},
                         {"speciality":"Dermatology","doctors":1,"appointments":2},
                         {"speciality":"Paediatrics","doctors":1,"appointments":1},
                         {"speciality":"Orthopaedics","doctors":1,"appointments":0}]""", JsonCompareMode.STRICT));
    }
}
