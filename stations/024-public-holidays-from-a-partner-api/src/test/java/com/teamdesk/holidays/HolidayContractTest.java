package com.teamdesk.holidays;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: a year's holidays, the provider's 404, and requests refused before any call is made. */
class HolidayContractTest extends ApiTest {

    @Test
    void aStatesHolidaysComeBackSortedInOurShape() throws Exception {
        holidays("2026", "ka")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.year").value(2026))
                .andExpect(jsonPath("$.state").value("KA"))
                .andExpect(jsonPath("$.holidays", hasSize(2)))
                .andExpect(jsonPath("$.holidays[0].date").value("2026-01-26"))
                .andExpect(jsonPath("$.holidays[0].name").value("Republic Day"))
                .andExpect(jsonPath("$.holidays[1].type").value("STATE"))
                .andExpect(jsonPath("$.holidays[0].observed").doesNotExist());   // the provider's extra fields stay out
        assertThat(STUB.lastQuery).isEqualTo("year=2026&region=KA");
    }

    @Test
    void theProvidersNotFoundIsOurNotFound() throws Exception {
        STUB.behaviour = StubProvider.Behaviour.NOT_FOUND;
        holidays("2026", "TN")
                .andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.detail").value("The provider has no holiday list for TN in 2026."));
    }

    @Test
    void badRequestsAre400AndNeverReachTheProvider() throws Exception {
        int before = STUB.calls.get();
        holidays("2026", "ZZ").andExpect(status().isBadRequest()).andExpect(jsonPath("$.title").value("Unknown state"));
        holidays("1999", "KA").andExpect(status().isBadRequest());
        holidays("abc", "KA").andExpect(status().isBadRequest());
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get("/holidays").param("state", "KA"))
                .andExpect(status().isBadRequest());
        assertThat(STUB.calls.get()).isEqualTo(before);
    }
}
