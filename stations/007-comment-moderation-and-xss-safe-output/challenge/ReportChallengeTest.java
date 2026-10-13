package com.chaupal.comments;

import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.ResultActions;

import java.util.UUID;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: members report a comment; three different reporters hide it. */
class ReportChallengeTest extends ApiTest {

    ResultActions report(String user, long postId, String commentId) throws Exception {
        return mvc.perform(post("/posts/{p}/comments/{c}/reports", postId, commentId).with(httpBasic(user, user + "-demo-pass")));
    }

    String commentId(String user, long postId, String text) throws Exception {
        String json = comment(user, postId, text).andReturn().getResponse().getContentAsString();
        return com.jayway.jsonpath.JsonPath.read(json, "$.id");
    }

    @Test
    void threeDifferentReportersHideTheComment() throws Exception {
        String id = commentId("ravi", 1, "Visit my shop for cheap phones");
        report("asha", 1, id).andExpect(status().isNoContent());
        report("kabir", 1, id).andExpect(status().isNoContent());
        mvc.perform(get("/posts/1/comments")).andExpect(jsonPath("$[0].id").value(id));   // two reports: still shown
        report("ravi", 1, id).andExpect(status().isNoContent());
        mvc.perform(get("/posts/1/comments")).andExpect(jsonPath("$").isEmpty());
    }

    @Test
    void reportingTwiceCountsOnce() throws Exception {
        String id = commentId("ravi", 1, "Hmm");
        report("asha", 1, id);
        report("asha", 1, id).andExpect(status().isNoContent());
        report("asha", 1, id);
        mvc.perform(get("/posts/1/comments")).andExpect(jsonPath("$[0].id").value(id));
    }

    @Test
    void anUnknownCommentOrAnInvisiblePostIs404() throws Exception {
        report("asha", 1, UUID.randomUUID().toString()).andExpect(status().isNotFound());
        String hidden = commentId("ravi", 2, "private note");
        report("asha", 2, hidden).andExpect(status().isNotFound());
    }

    @Test
    void mutedUsersCannotReport() throws Exception {
        String id = commentId("ravi", 1, "Hello");
        report("tara", 1, id).andExpect(status().isForbidden());
    }
}
