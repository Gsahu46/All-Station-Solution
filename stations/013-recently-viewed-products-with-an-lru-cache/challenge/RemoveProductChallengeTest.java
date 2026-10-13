package com.kartwala.recent;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: the "x" on a product in the strip: DELETE /users/{id}/recently-viewed/{productId}, safe to repeat. */
class RemoveProductChallengeTest extends ApiTest {

    @Test
    void removingAProductIs204AndItIsGone() throws Exception {
        view(7, 101);
        view(7, 102);
        mvc.perform(delete("/users/7/recently-viewed/101")).andExpect(status().isNoContent());
        mvc.perform(get("/users/7/recently-viewed")).andExpect(jsonPath("$.productIds", contains(102)));
    }

    @Test
    void removingTwiceOrRemovingSomethingNeverViewedIsStill204() throws Exception {
        view(7, 101);
        mvc.perform(delete("/users/7/recently-viewed/101")).andExpect(status().isNoContent());
        mvc.perform(delete("/users/7/recently-viewed/101")).andExpect(status().isNoContent());
        mvc.perform(delete("/users/99/recently-viewed/5")).andExpect(status().isNoContent());
    }
}
