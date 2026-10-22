package com.paysetu.cards;

import org.junit.jupiter.api.Test;

import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class TokenPaymentTest extends ApiTest {

    @Test
    void aPaymentWithASavedCardUsesItsToken() throws Exception {
        long card = savedCardId("asha", ASHA, VISA);
        pay("asha", "ord-100", card, 129900).andExpect(status().isCreated()).andExpect(jsonPath("$.orderId").value("ORD-100"))
                .andExpect(jsonPath("$.status").value("succeeded")).andExpect(jsonPath("$.networkRef").value("auth_2"));
        pay("asha", "ORD-101", card, 129951).andExpect(status().isPaymentRequired()).andExpect(jsonPath("$.status").value("declined"));
    }

    @Test
    void theSameOrderTwiceIsOnePayment() throws Exception {
        long card = savedCardId("asha", ASHA, VISA);
        String first = pay("asha", "ORD-200", card, 50000).andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
        String again = pay("asha", "ORD-200", card, 50000).andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
        assertThat(again).isEqualTo(first);
        assertThat(jdbc.sql("SELECT count(*) FROM payments").query(Long.class).single()).isOne();
    }

    @Test
    void aRetryAfterTheCardExpiredStillGetsTheFirstAnswer() throws Exception {
        long card = savedCardId("asha", ASHA, VISA);
        String first = pay("asha", "ORD-250", card, 50000).andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
        CLOCK.now = Instant.parse("2029-02-01T00:00:00Z");
        String again = pay("asha", "ORD-250", card, 50000).andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
        assertThat(again).isEqualTo(first);   // the payment happened; the card's later state does not change that answer
    }

    @Test
    void anExpiredSavedCardIs422() throws Exception {
        long card = savedCardId("asha", ASHA, VISA);   // expires 12/2028
        CLOCK.now = Instant.parse("2028-12-31T18:29:59Z");   // 23:59:59 IST on 31 Dec 2028: still valid
        pay("asha", "ORD-300", card, 50000).andExpect(status().isCreated());
        CLOCK.now = Instant.parse("2028-12-31T18:30:00Z");   // 00:00 IST on 1 Jan 2029
        pay("asha", "ORD-301", card, 50000).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.detail").value("This saved card has expired; save the new card"));
    }

    @Test
    void badPaymentRequestsAre400() throws Exception {
        long card = savedCardId("asha", ASHA, VISA);
        pay("asha", "OR", card, 50000).andExpect(status().isBadRequest());
        pay("asha", "ORD-400", card, 99).andExpect(status().isBadRequest());
        pay("asha", "ORD-400", 0, 50000).andExpect(status().isBadRequest());
        pay("asha", "ORD-400", 99, 50000).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No such saved card"));
    }
}
