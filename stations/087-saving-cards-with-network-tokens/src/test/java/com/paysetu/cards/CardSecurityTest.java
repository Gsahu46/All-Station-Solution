package com.paysetu.cards;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class CardSecurityTest extends ApiTest {

    @Test
    void withoutAValidSignInEverythingIs401() throws Exception {
        mvc.perform(get("/customers/1/saved-cards")).andExpect(status().isUnauthorized()).andExpect(jsonPath("$.title").value("Sign-in required"));
        mvc.perform(get("/customers/1/saved-cards").with(httpBasic("asha", "wrong"))).andExpect(status().isUnauthorized());
        mvc.perform(post("/payments").contentType(MediaType.APPLICATION_JSON).content("{}")).andExpect(status().isUnauthorized());
    }

    @Test
    void oneCustomerCannotSeeOrAddToAnothersCards() throws Exception {
        long ashasCard = savedCardId("asha", ASHA, VISA);
        list("rohan", ASHA).andExpect(status().isForbidden()).andExpect(jsonPath("$.title").value("Not allowed"));
        save("rohan", ASHA, MASTERCARD, 1, 2027).andExpect(status().isForbidden());
        pay("rohan", "ORD-500", ashasCard, 50000).andExpect(status().isNotFound());   // not "forbidden": that would confirm the card exists
        assertThat(jdbc.sql("SELECT count(*) FROM saved_cards").query(Long.class).single()).isOne();
        assertThat(jdbc.sql("SELECT count(*) FROM payments").query(Long.class).single()).isZero();
    }

    @Test
    void anOrderIdBelongsToOneCustomer() throws Exception {
        long ashasCard = savedCardId("asha", ASHA, VISA);
        long rohansCard = savedCardId("rohan", ROHAN, MASTERCARD);
        pay("asha", "ORD-600", ashasCard, 50000).andExpect(status().isCreated());
        pay("rohan", "ORD-600", rohansCard, 50000).andExpect(status().isConflict());   // never Asha's payment in Rohan's answer
    }

    @Test
    void maliciousInputIsRefusedBeforeAnythingRuns() throws Exception {
        save("asha", ASHA, "{\"cardNumber\":\"4111' OR '1'='1\",\"expiryMonth\":12,\"expiryYear\":2028,\"consent\":true}").andExpect(status().isBadRequest());
        save("asha", ASHA, "{\"cardNumber\":\"" + "4".repeat(5000) + "\",\"expiryMonth\":12,\"expiryYear\":2028,\"consent\":true}").andExpect(status().isBadRequest());
        pay("asha", "ORD-1;DROP TABLE payments", 1, 50000).andExpect(status().isBadRequest());
        mvc.perform(get("/customers/1/saved-cards/../../payments").with(httpBasic("asha", password("asha")))).andExpect(status().is4xxClientError());
        assertThat(network.holds("4".repeat(5000))).isFalse();
    }
}
