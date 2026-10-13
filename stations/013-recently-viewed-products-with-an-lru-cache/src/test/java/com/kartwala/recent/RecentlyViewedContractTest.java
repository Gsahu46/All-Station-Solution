package com.kartwala.recent;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: newest first, no duplicates, at most 10, and the refusals. */
class RecentlyViewedContractTest extends ApiTest {

    @Test
    void viewsAreListedNewestFirst() throws Exception {
        view(7, 101);
        view(7, 102);
        view(7, 103).andExpect(status().isOk())
                .andExpect(jsonPath("$.userId").value(7))
                .andExpect(jsonPath("$.productIds", contains(103, 102, 101)));
        mvc.perform(get("/users/7/recently-viewed")).andExpect(jsonPath("$.productIds", contains(103, 102, 101)));
    }

    @Test
    void viewingAgainMovesTheProductToTheFrontWithoutADuplicate() throws Exception {
        view(7, 101);
        view(7, 102);
        view(7, 101).andExpect(jsonPath("$.productIds", contains(101, 102)));
    }

    @Test
    void theEleventhProductPushesOutTheOldest() throws Exception {
        for (long p = 1; p <= 11; p++) {
            view(7, p);
        }
        mvc.perform(get("/users/7/recently-viewed"))
                .andExpect(jsonPath("$.productIds", hasSize(10)))
                .andExpect(jsonPath("$.productIds[0]").value(11))
                .andExpect(jsonPath("$.productIds[9]").value(2));   // product 1 is gone
    }

    @Test
    void reViewingAnOldProductSavesItFromEviction() throws Exception {
        for (long p = 1; p <= 10; p++) {
            view(7, p);
        }
        view(7, 1);            // product 1 is used again, so product 2 is now the least recent
        view(7, 11);
        mvc.perform(get("/users/7/recently-viewed")).andExpect(jsonPath("$.productIds", contains(11, 1, 10, 9, 8, 7, 6, 5, 4, 3)));
    }

    @Test
    void usersHaveSeparateHistoriesAndANewUserHasNone() throws Exception {
        view(7, 101);
        view(8, 201);
        mvc.perform(get("/users/8/recently-viewed")).andExpect(jsonPath("$.productIds", contains(201)));
        mvc.perform(get("/users/9/recently-viewed")).andExpect(status().isOk()).andExpect(jsonPath("$.productIds", hasSize(0)));
    }

    @Test
    void badInputIs400() throws Exception {
        view(0, 101).andExpect(status().isBadRequest()).andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
        view(7, -5).andExpect(status().isBadRequest());
        mvc.perform(post("/users/7/recently-viewed").contentType(MediaType.APPLICATION_JSON).content("{}")).andExpect(status().isBadRequest());
        mvc.perform(get("/users/abc/recently-viewed")).andExpect(status().isBadRequest());
    }
}
