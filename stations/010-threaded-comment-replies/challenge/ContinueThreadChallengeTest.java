package com.chaupal.threads;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: "Continue this thread": rootId starts the tree at one comment, so the app can open what was cut off. */
class ContinueThreadChallengeTest extends ApiTest {

    @Test
    void theTreeStartsAtTheGivenComment() throws Exception {
        mvc.perform(get("/posts/2/comment-tree").param("rootId", "200006").param("maxDepth", "2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.comments[0].id").value(200006))
                .andExpect(jsonPath("$.comments[0].replies[0].id").value(200007))
                .andExpect(jsonPath("$.comments[0].replies[0].moreReplies").value(99_993));
    }

    @Test
    void aSmallSubtreeOnPostOne() throws Exception {
        mvc.perform(get("/posts/1/comment-tree").param("rootId", "2"))
                .andExpect(jsonPath("$.comments[0].replies[0].replies[0].replies[0].text").value("Closed on Mondays though."));
    }

    @Test
    void anUnknownCommentOrOneFromAnotherPostIs404() throws Exception {
        mvc.perform(get("/posts/1/comment-tree").param("rootId", "12345")).andExpect(status().isNotFound());
        mvc.perform(get("/posts/1/comment-tree").param("rootId", "200006")).andExpect(status().isNotFound());
    }
}
