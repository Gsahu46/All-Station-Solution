package com.chaupal.threads;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: the tree's shape and order, the depth limit, and every way a request can be refused. */
class CommentTreeContractTest extends ApiTest {

    @Test
    void repliesAreNestedUnderTheCommentTheyAnswerOldestFirst() throws Exception {
        mvc.perform(get("/posts/1/comment-tree"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.postId").value(1))
                .andExpect(jsonPath("$.maxDepth").value(5))
                .andExpect(jsonPath("$.comments[*].id", contains(1, 6)))
                .andExpect(jsonPath("$.comments[0].replies[*].id", contains(2, 3)))       // same minute: ordered by id
                .andExpect(jsonPath("$.comments[0].replies[0].replies[0].id").value(4))
                .andExpect(jsonPath("$.comments[0].replies[0].replies[0].replies[0].replies[0].text").value("Closed on Mondays though."))
                .andExpect(jsonPath("$.comments[1].replies[0].text").value("Not yet!"))
                .andExpect(jsonPath("$.comments[0].moreReplies").value(0));
    }

    @Test
    void atTheDepthLimitRepliesAreCountedNotShown() throws Exception {
        mvc.perform(get("/posts/1/comment-tree").param("maxDepth", "2"))
                .andExpect(jsonPath("$.comments[0].replies[0].id").value(2))
                .andExpect(jsonPath("$.comments[0].replies[0].replies").isEmpty())
                .andExpect(jsonPath("$.comments[0].replies[0].moreReplies").value(3))  // 4, 5 and 8 below comment 2
                .andExpect(jsonPath("$.comments[0].replies[1].moreReplies").value(1));
    }

    @Test
    void maxDepthOneShowsOnlyTopLevelComments() throws Exception {
        mvc.perform(get("/posts/1/comment-tree").param("maxDepth", "1"))
                .andExpect(jsonPath("$.comments[0].replies").isEmpty())
                .andExpect(jsonPath("$.comments[0].moreReplies").value(6))
                .andExpect(jsonPath("$.comments[1].moreReplies").value(1));
    }

    @Test
    void aPostWithNoCommentsIsAnEmptyTree() throws Exception {
        mvc.perform(get("/posts/3/comment-tree")).andExpect(status().isOk()).andExpect(jsonPath("$.comments").isEmpty());
    }

    @Test
    void maxDepthOutsideOneToTenIs400() throws Exception {
        for (String bad : new String[]{"0", "11", "100000", "-1"}) {
            mvc.perform(get("/posts/1/comment-tree").param("maxDepth", bad))
                    .andExpect(status().isBadRequest())
                    .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                    .andExpect(jsonPath("$.errors.maxDepth").exists());
        }
        mvc.perform(get("/posts/1/comment-tree").param("maxDepth", "deep")).andExpect(status().isBadRequest());
    }

    @Test
    void anUnknownPostIs404() throws Exception {
        mvc.perform(get("/posts/99/comment-tree")).andExpect(status().isNotFound())
                .andExpect(jsonPath("$.title").value("Post not found"));
    }
}
