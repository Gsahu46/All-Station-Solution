package com.kartwala.export;

import org.junit.jupiter.api.Test;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /seller/exports lists the seller's own exports, newest first, each with the number of orders it
 * sent. The number is known only when the stream ends: a V3 migration adds rows_sent, filled in after the last row.
 */
class ExportHistoryChallengeTest extends ApiTest {

    @Test
    void aSellerSeesTheirOwnExportsWithHowManyOrdersEachSent() throws Exception {
        export("neha.store", "2026-01-01", "2026-12-31");
        export("neha.store", "2026-06-30", "2026-06-30");
        export("arun.mart", "2026-01-01", "2026-12-31");
        mvc.perform(get("/seller/exports").with(httpBasic("neha.store", password("neha.store")))).andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[0].from").value("2026-06-30")).andExpect(jsonPath("$[0].rowsSent").value(1))
                .andExpect(jsonPath("$[1].rowsSent").value(5));
        mvc.perform(get("/seller/exports").with(httpBasic("arun.mart", password("arun.mart")))).andExpect(jsonPath("$.length()").value(1));
    }

    @Test
    void supportAndStrangersCannotSeeIt() throws Exception {
        mvc.perform(get("/seller/exports").with(httpBasic("sam.help", password("sam.help")))).andExpect(status().isForbidden());
        mvc.perform(get("/seller/exports")).andExpect(status().isUnauthorized());
        mvc.perform(get("/seller/exports").with(httpBasic("neha.store", password("neha.store")))).andExpect(content().json("[]"));
    }
}
