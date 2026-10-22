package com.paysetu.cards;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class SavedCardContractTest extends ApiTest {

    @Test
    void aSavedCardShowsOnlyWhatTheCustomerNeedsToRecogniseIt() throws Exception {
        save("asha", ASHA, "4111 1111 1111 1111", 12, 2028).andExpect(status().isCreated()).andExpect(jsonPath("$.id").value(1))
                .andExpect(jsonPath("$.network").value("VISA")).andExpect(jsonPath("$.last4").value("1111"))
                .andExpect(jsonPath("$.expiryMonth").value(12)).andExpect(jsonPath("$.expiryYear").value(2028))
                .andExpect(jsonPath("$.tokenRef").doesNotExist()).andExpect(jsonPath("$.cardNumber").doesNotExist());
        save("asha", ASHA, MASTERCARD, 1, 2027).andExpect(jsonPath("$.network").value("MASTERCARD"));
        save("asha", ASHA, RUPAY, 1, 2027).andExpect(jsonPath("$.network").value("RUPAY"));
        list("asha", ASHA).andExpect(status().isOk()).andExpect(jsonPath("$.length()").value(3)).andExpect(jsonPath("$[2].last4").value("0015"));
        list("rohan", ROHAN).andExpect(status().isOk()).andExpect(content().json("[]"));
    }

    @Test
    void badCardsAre400AndRefusedOnesAre422() throws Exception {
        save("asha", ASHA, "4111111111111112", 12, 2028).andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detail").value("This is not a valid card number"));
        save("asha", ASHA, "41111113", 12, 2028).andExpect(status().isBadRequest());   // passes the check digit, far too short
        save("asha", ASHA, "4111-1111-1111-1111", 12, 2028).andExpect(status().isBadRequest());
        save("asha", ASHA, VISA, 13, 2028).andExpect(status().isBadRequest());
        save("asha", ASHA, "{\"cardNumber\":\"" + VISA + "\",\"expiryMonth\":12,\"expiryYear\":2028}").andExpect(status().isBadRequest());   // no consent
        save("asha", ASHA, VISA, 9, 2026).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.detail").value("This card has expired"));
        save("asha", ASHA, "378282246310005", 12, 2028).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.detail").value("This card network is not supported"));
        assertThat(jdbc.sql("SELECT count(*) FROM saved_cards").query(Long.class).single()).isZero();
    }
}
