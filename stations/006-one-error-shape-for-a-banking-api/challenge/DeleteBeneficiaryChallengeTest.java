package com.tijori.beneficiaries;

import org.junit.jupiter.api.Test;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: DELETE /beneficiaries/{id}, with the same error shape and the same ownership rule as GET. */
class DeleteBeneficiaryChallengeTest extends ApiTest {

    @Test
    void theOwnerDeletesIt204AndItIsGone() throws Exception {
        String location = add("asha", ravisAccount()).andReturn().getResponse().getHeader("Location");
        mvc.perform(delete(location).with(httpBasic("asha", "asha-demo-pass"))).andExpect(status().isNoContent());
        mvc.perform(get(location).with(httpBasic("asha", "asha-demo-pass"))).andExpect(status().isNotFound());
    }

    @Test
    void anotherCustomerCannotDeleteItAndLearnsNothing() throws Exception {
        String location = add("asha", ravisAccount()).andReturn().getResponse().getHeader("Location");
        mvc.perform(delete(location).with(httpBasic("ravi", "ravi-demo-pass")))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.type").value("https://tijori.example/problems/beneficiary-not-found"));
        mvc.perform(get(location).with(httpBasic("asha", "asha-demo-pass"))).andExpect(status().isOk());
    }

    @Test
    void aViewerCannotDelete403() throws Exception {
        String location = add("asha", ravisAccount()).andReturn().getResponse().getHeader("Location");
        mvc.perform(delete(location).with(httpBasic("meera", "meera-demo-pass")))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.type").value("https://tijori.example/problems/forbidden"));
    }
}
