package com.mediqo.roster;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: PUT /rosters/{ward}/minimum {minOnCall}. A minimum above the doctors on call right now is refused (409),
 * by the API and by the database (a V3 migration), because raising it is the same write skew seen from the other side.
 */
class MinimumChallengeTest extends ApiTest {

    ResultActions minimum(String ward, String body) throws Exception {
        return mvc.perform(put("/rosters/{ward}/minimum", ward).contentType(MediaType.APPLICATION_JSON).content(body));
    }

    @Test
    void aHigherMinimumThenStopsTheNextOffCall() throws Exception {
        minimum("cardiology", "{\"minOnCall\": 2}").andExpect(status().isOk()).andExpect(jsonPath("$.minOnCall").value(2));
        offCall("cardiology", "dr.sharma").andExpect(status().isConflict()).andExpect(jsonPath("$.detail").value("Cardiology needs at least 2 doctor on call"));
    }

    @Test
    void aMinimumAboveWhoIsOnCallIsRefused() throws Exception {
        minimum("cardiology", "{\"minOnCall\": 3}").andExpect(status().isConflict()).andExpect(jsonPath("$.detail").value("Cardiology has only 2 doctor on call"));
        minimum("cardiology", "{\"minOnCall\": 0}").andExpect(status().isBadRequest());
        minimum("neurology", "{\"minOnCall\": 1}").andExpect(status().isNotFound());
        assertThat(jdbc.sql("SELECT min_on_call FROM wards WHERE id = 'cardiology'").query(Integer.class).single()).isEqualTo(1);
    }

    @Test
    void theDatabaseRefusesItToo() {
        assertThatThrownBy(() -> jdbc.sql("UPDATE wards SET min_on_call = 3 WHERE id = 'cardiology'").update())
                .hasMessageContaining("wards_minimum_is_met");
    }
}
