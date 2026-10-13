package com.rydo.fares;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/** Challenge 1: Rydo launches EV_CAB: Rs 50 base, Rs 12 per km, Rs 80 minimum. No other fare may change. */
class EvCabChallengeTest extends ApiTest {

    @Test
    void evCabsAreEstimatedAndNothingElseMoves() throws Exception {
        mvc.perform(get("/fare-estimates").param("pickup", "12.9756,77.6066").param("drop", "12.9352,77.6245"))
                .andExpect(jsonPath("$.estimates[?(@.vehicle == 'EV_CAB')].farePaise", contains(12700)))   // 126.80 -> 127
                .andExpect(jsonPath("$.estimates[?(@.vehicle == 'AUTO')].farePaise", contains(9600)))
                .andExpect(jsonPath("$.estimates[?(@.vehicle == 'CAB')].farePaise", contains(14000)));
    }
}
