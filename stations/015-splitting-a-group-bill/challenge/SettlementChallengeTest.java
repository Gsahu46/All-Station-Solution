package com.splitsaathi.groups;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: POST /groups/{id}/settlements records a payment between two members, so balances move towards zero. */
class SettlementChallengeTest extends ApiTest {

    void settle(String from, String to, long paise, int expectedStatus) throws Exception {
        mvc.perform(post("/groups/1/settlements").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"from\":\"" + from + "\",\"to\":\"" + to + "\",\"amountPaise\":" + paise + "}"))
                .andExpect(status().is(expectedStatus));
    }

    @Test
    void payingTheSuggestedPaymentsLeavesNothingToSettle() throws Exception {
        expense(1, """
                {"description":"Dinner","paidBy":"asha","amountPaise":90000,"splitType":"EQUAL","participants":["asha","ravi","meera"]}""");
        settle("ravi", "asha", 30000, 201);
        mvc.perform(get("/groups/1/settle-up"))
                .andExpect(jsonPath("$.balancesPaise.ravi").value(0))
                .andExpect(jsonPath("$.payments", hasSize(1)));
        settle("meera", "asha", 30000, 201);
        mvc.perform(get("/groups/1/settle-up")).andExpect(jsonPath("$.payments", hasSize(0)));
    }

    @Test
    void badSettlementsAreRefused() throws Exception {
        settle("ravi", "ravi", 100, 422);     // to yourself
        settle("ravi", "neha", 100, 422);     // not in this group
        settle("ravi", "asha", 0, 400);       // nothing paid
    }
}
