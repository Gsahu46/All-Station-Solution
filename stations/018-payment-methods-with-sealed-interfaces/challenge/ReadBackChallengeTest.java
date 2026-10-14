package com.paysetu.payments;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.matchesPattern;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: keep each intent, answer GET /payment-intents/{id}, and point to it with a Location header. */
class ReadBackChallengeTest extends ApiTest {

    @Test
    void anIntentCanBeReadBackWithoutItsCardToken() throws Exception {
        String location = intent("{\"type\":\"CARD\",\"network\":\"VISA\",\"last4\":\"1111\",\"token\":\"tok_a1b2c3d4e5f6\"}")
                .andExpect(header().string("Location", matchesPattern("/payment-intents/pi_[0-9a-f]{32}")))
                .andReturn().getResponse().getHeader("Location");
        mvc.perform(get(location))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(location.substring("/payment-intents/".length())))
                .andExpect(jsonPath("$.method.type").value("CARD"))
                .andExpect(jsonPath("$.method.token").doesNotExist());
    }

    @Test
    void anUnknownIntentIs404() throws Exception {
        mvc.perform(get("/payment-intents/pi_00000000000000000000000000000000"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.title").value("Payment intent not found"));
    }
}
