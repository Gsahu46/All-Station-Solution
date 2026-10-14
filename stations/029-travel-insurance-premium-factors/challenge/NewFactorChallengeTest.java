package com.bimaly.premiums;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 1: a pre-existing medical condition adds 40% to the cover cost (after age, before the adventure add-on).
 * Add the factor without editing PremiumCalculator: a new bean with the right @Order is enough.
 */
@SpringBootTest
@AutoConfigureMockMvc
class NewFactorChallengeTest {

    @Autowired
    MockMvc mvc;

    @Test
    void aPreExistingConditionIsLoadedBeforeTheAdventureAddOn() throws Exception {
        mvc.perform(post("/premium-quotes").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"age\":67,\"destination\":\"EUROPE\",\"days\":10,\"adventureSports\":true,\"preExistingCondition\":true}"))
                .andExpect(jsonPath("$.breakdown[3].factor").value("pre-existing condition"))
                .andExpect(jsonPath("$.breakdown[3].totalPaise").value(187_425))   // 133,875 x 1.40
                .andExpect(jsonPath("$.premiumPaise").value(237_500));             // + 50,000 adventure, rounded up
        mvc.perform(post("/premium-quotes").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"age\":67,\"destination\":\"EUROPE\",\"days\":10,\"adventureSports\":true}"))
                .andExpect(jsonPath("$.premiumPaise").value(183_900));
    }
}
