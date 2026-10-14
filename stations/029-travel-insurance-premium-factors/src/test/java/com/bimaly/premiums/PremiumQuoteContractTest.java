package com.bimaly.premiums;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: quotes with their breakdown, the minimum, rounding up, and every refusal. */
@SpringBootTest
@AutoConfigureMockMvc
class PremiumQuoteContractTest {

    @Autowired
    MockMvc mvc;

    ResultActions quote(String json) throws Exception {
        return mvc.perform(post("/premium-quotes").contentType(MediaType.APPLICATION_JSON).content(json));
    }

    @Test
    void aQuoteShowsEveryFactorInOrder() throws Exception {
        quote("{\"age\":67,\"destination\":\"EUROPE\",\"days\":10,\"adventureSports\":true}")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.premiumPaise").value(183_900))   // Rs 1,838.75, rounded up
                .andExpect(jsonPath("$.perDayPaise").value(18_400))     // Rs 183.90 a day, shown to the nearest rupee
                .andExpect(jsonPath("$.breakdown[0].factor").value("base"))   // steps looked up by name: a new factor must not break this
                .andExpect(jsonPath("$.breakdown[?(@.factor == 'base')].totalPaise").value(42_500))
                .andExpect(jsonPath("$.breakdown[?(@.factor == 'destination')].totalPaise").value(74_375))
                .andExpect(jsonPath("$.breakdown[?(@.factor == 'age')].note").value("age 67 x 1.80"))
                .andExpect(jsonPath("$.breakdown[?(@.factor == 'age')].totalPaise").value(133_875))
                .andExpect(jsonPath("$.breakdown[?(@.factor == 'adventure')].totalPaise").value(183_875))
                .andExpect(jsonPath("$.breakdown[-1:].factor").value("minimum"));
    }

    @Test
    void aShortCheapTripPaysTheMinimum() throws Exception {
        quote("{\"age\":25,\"destination\":\"ASIA\",\"days\":3}")
                .andExpect(jsonPath("$.premiumPaise").value(19_900))
                .andExpect(jsonPath("$.breakdown[?(@.factor == 'minimum')].note").value("raised to the Rs 199.00 minimum"));
    }

    @Test
    void paiseAreRoundedUpToTheNextRupee() throws Exception {
        quote("{\"age\":45,\"destination\":\"USA_CANADA\",\"days\":7}").andExpect(jsonPath("$.premiumPaise").value(106_400));   // from 106,357
        quote("{\"age\":45,\"destination\":\"EUROPE\",\"days\":5}").andExpect(jsonPath("$.premiumPaise").value(48_400));     // from 48,344: up, not nearest
    }

    @Test
    void travellersOver80Are422() throws Exception {
        quote("{\"age\":81,\"destination\":\"ASIA\",\"days\":3}")
                .andExpect(status().isUnprocessableContent())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.title").value("No online cover for this age"));
        quote("{\"age\":80,\"destination\":\"ASIA\",\"days\":3}").andExpect(status().isOk());
    }

    @Test
    void badRequestsAre400() throws Exception {
        quote("{\"age\":30,\"destination\":\"MARS\",\"days\":3}").andExpect(status().isBadRequest());
        quote("{\"age\":30,\"destination\":\"ASIA\",\"days\":0}").andExpect(status().isBadRequest());
        quote("{\"age\":30,\"destination\":\"ASIA\",\"days\":181}").andExpect(status().isBadRequest());
        quote("{\"age\":-1,\"destination\":\"ASIA\",\"days\":3}").andExpect(status().isBadRequest());
        quote("{\"destination\":\"ASIA\",\"days\":3}").andExpect(status().isBadRequest());
    }
}
