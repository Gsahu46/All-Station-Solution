package com.mediqo.doctors;

import org.junit.jupiter.api.Test;
import org.springframework.test.json.JsonCompareMode;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;

/**
 * Challenge 2: GET /specialities: each speciality with how many doctors, most first, then by name. Count in the
 * database with a JPQL query and a projection, not by loading every doctor into Java.
 */
class SpecialityCountChallengeTest extends ApiTest {

    @Test
    void specialitiesWithTheirDoctorCounts() throws Exception {
        mvc.perform(get("/specialities")).andExpect(content().json("""
                [{"speciality":"Cardiology","doctors":3},{"speciality":"Dermatology","doctors":1},
                 {"speciality":"Orthopaedics","doctors":1},{"speciality":"Paediatrics","doctors":1}]""", JsonCompareMode.STRICT));
    }
}
