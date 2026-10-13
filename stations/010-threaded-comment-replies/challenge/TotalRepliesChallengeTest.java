package com.chaupal.threads;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/** Challenge 1: every comment shows how many replies it has in total, at any depth ("12 replies"). */
class TotalRepliesChallengeTest extends ApiTest {

    @Test
    void everyNodeCountsAllItsReplies() throws Exception {
        mvc.perform(get("/posts/1/comment-tree"))
                .andExpect(jsonPath("$.comments[0].totalReplies").value(6))
                .andExpect(jsonPath("$.comments[0].replies[0].totalReplies").value(3))
                .andExpect(jsonPath("$.comments[0].replies[1].totalReplies").value(1))
                .andExpect(jsonPath("$.comments[1].totalReplies").value(1))
                .andExpect(jsonPath("$.comments[1].replies[0].totalReplies").value(0));
    }

    @Test
    void theDeepThreadIsCountedWithoutCrashing() throws Exception {
        mvc.perform(get("/posts/2/comment-tree").param("maxDepth", "2"))
                .andExpect(jsonPath("$.comments[0].totalReplies").value(99_999))
                .andExpect(jsonPath("$.comments[0].replies[0].totalReplies").value(99_998));
    }
}
