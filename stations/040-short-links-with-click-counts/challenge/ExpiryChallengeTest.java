package com.chhotu.links;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import java.time.OffsetDateTime;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: campaign links may end. An optional "expiresAt" (must be in the future when the link is made); after
 * it, following the link is 410 Gone (it existed, and will not come back), while its stats stay readable.
 */
class ExpiryChallengeTest extends ApiTest {

    String createExpiring(OffsetDateTime at, int expectedStatus) throws Exception {
        return mvc.perform(post("/links").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"targetUrl\":\"https://shop.example/sale\",\"expiresAt\":\"" + at + "\"}"))
                .andExpect(status().is(expectedStatus))
                .andReturn().getResponse().getContentAsString().replaceAll(".*\"code\":\"([^\"]+)\".*", "$1");
    }

    @Test
    void anExpiredLinkIsGoneButItsStatsRemain() throws Exception {
        String code = createExpiring(OffsetDateTime.now().plusDays(7), 201);
        follow(code).andExpect(status().isFound());
        jdbc.sql("UPDATE links SET expires_at = now() - interval '1 minute' WHERE code = ?").param(code).update();
        follow(code).andExpect(status().isGone());
        mvc.perform(get("/links/{c}/stats", code)).andExpect(status().isOk());
    }

    @Test
    void anExpiryInThePastIsRefused() throws Exception {
        createExpiring(OffsetDateTime.now().minusDays(1), 400);
    }
}
