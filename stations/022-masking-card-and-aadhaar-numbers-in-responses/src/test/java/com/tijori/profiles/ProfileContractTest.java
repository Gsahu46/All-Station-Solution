package com.tijori.profiles;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: the masked profile, field by field, and a profile that does not exist. */
class ProfileContractTest extends ApiTest {

    @Test
    void aCustomerSeesTheirOwnProfileMaskedFieldByField() throws Exception {
        profileAs("ravi", "c-1002")
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.customerId").value("c-1002"))
                .andExpect(jsonPath("$.name").value("Ravi Kumar"))
                .andExpect(jsonPath("$.mobile").value("XXXXXX6780"))
                .andExpect(jsonPath("$.email").value("r***@example.com"))
                .andExpect(jsonPath("$.aadhaar").value("XXXX XXXX 1234"))
                .andExpect(jsonPath("$.cards", hasSize(2)))
                .andExpect(jsonPath("$.cards[0].network").value("MASTERCARD"))
                .andExpect(jsonPath("$.cards[0].number").value("XXXX XXXX XXXX 4444"))
                .andExpect(jsonPath("$.cards[0].expiry").value("01/28"))
                .andExpect(jsonPath("$.cards[1].number").value("XXXX XXXX XXXX 1881"))
                .andExpect(jsonPath("$.bankAccount").value("XXXXXXXXXX3344"));
    }

    @Test
    void aProfileThatDoesNotExistIs404() throws Exception {
        profileAs("neha", "c-9999")
                .andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.title").value("Profile not found"));
    }
}
