package com.mediqo.reports;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.nullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 1: add "noShowPercent": no-shows as a whole-number percentage of appointments, rounded. A doctor with no
 * appointments has no rate at all (null), not 0% and not a division-by-zero error.
 */
class NoShowRateChallengeTest extends ApiTest {

    @Test
    void theRateIsRoundedAndMissingWhenThereIsNothingToDivide() throws Exception {
        mvc.perform(get("/reports/doctor-load").param("from", FROM).param("to", TO))
                .andExpect(jsonPath("$.doctors[*].name", contains("Dr Mehta", "Dr Iyer", "Dr Rao", "Dr Khan")))
                .andExpect(jsonPath("$.doctors[0].noShowPercent").value(33))
                .andExpect(jsonPath("$.doctors[1].noShowPercent").value(0))
                .andExpect(jsonPath("$.doctors[3].noShowPercent").value(nullValue()));
    }
}
