package com.citylibrary.loans;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: POST /members/{id}/fine-payments with {"amountPaise": 1000} pays part or all of a fine (a record of a
 * payment at the desk; no money moves here). Paying more than is owed is 422. Once paid in full, loans work again.
 */
class PayFineChallengeTest extends ApiTest {

    ResultActions pay(String member, long paise) throws Exception {
        return mvc.perform(post("/members/{id}/fine-payments", member).contentType(MediaType.APPLICATION_JSON)
                .content("{\"amountPaise\":" + paise + "}"));
    }

    @Test
    void payingTheWholeFineLiftsTheBlock() throws Exception {
        pay("m-2", 500).andExpect(status().isOk()).andExpect(jsonPath("$.unpaidFinePaise").value(1_500));
        borrow("m-2", "b-1").andExpect(status().isConflict());
        pay("m-2", 1_500).andExpect(jsonPath("$.unpaidFinePaise").value(0));
        borrow("m-2", "b-1").andExpect(status().isCreated());
    }

    @Test
    void payingTooMuchOrNothingIsRefused() throws Exception {
        pay("m-2", 2_001).andExpect(status().isUnprocessableContent());
        pay("m-2", 0).andExpect(status().isBadRequest());
        pay("m-9", 100).andExpect(status().isNotFound());
    }
}
