package com.mapwise.geocode;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: tell partners what is left before they hit the wall. Every request that passes the key check gets
 * X-RateLimit-Remaining (whole requests left in the bucket) and X-Quota-Remaining (requests left today).
 */
class RemainingHeadersChallengeTest extends ApiTest {

    @Test
    void everyAnswerSaysWhatIsLeft() throws Exception {
        geocode(CHALO, "MG Road, Bengaluru").andExpect(status().isOk())
                .andExpect(header().string("X-RateLimit-Remaining", "2")).andExpect(header().string("X-Quota-Remaining", "19"));
        geocode(CHALO, "Nowhere Lane, Atlantis").andExpect(status().isNotFound())
                .andExpect(header().string("X-RateLimit-Remaining", "1")).andExpect(header().string("X-Quota-Remaining", "18"));
        geocode(CHALO, "MG Road, Bengaluru").andExpect(header().string("X-RateLimit-Remaining", "0"));
        geocode(CHALO, "MG Road, Bengaluru").andExpect(status().isTooManyRequests())
                .andExpect(header().string("X-RateLimit-Remaining", "0")).andExpect(header().string("X-Quota-Remaining", "17"));
    }

    @Test
    void noHeadersForAnUnknownKey() throws Exception {
        geocode("mw_demo_nobody", "MG Road, Bengaluru").andExpect(status().isUnauthorized())
                .andExpect(header().doesNotExist("X-RateLimit-Remaining")).andExpect(header().doesNotExist("X-Quota-Remaining"));
    }
}
