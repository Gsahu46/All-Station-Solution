package com.taskloom.board;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: PATCH /tasks/{id} with a JSON merge patch (application/merge-patch+json, RFC 7396) changes only the
 * fields sent. The same rules as PUT: If-Match required (428), an old ETag is 412.
 */
class PatchChallengeTest extends ApiTest {

    @Test
    void onlyTheFieldsSentChange() throws Exception {
        mvc.perform(patch("/tasks/1").header("If-Match", etag(1)).contentType(MediaType.valueOf("application/merge-patch+json")).content("{\"status\":\"done\"}"))
                .andExpect(status().isOk()).andExpect(header().string("ETag", "\"1\""))
                .andExpect(jsonPath("$.status").value("done")).andExpect(jsonPath("$.assignee").value("asha")).andExpect(jsonPath("$.title").value("Write the press release"));
    }

    @Test
    void theSameRulesAsPut() throws Exception {
        mvc.perform(patch("/tasks/1").contentType(MediaType.valueOf("application/merge-patch+json")).content("{\"status\":\"done\"}")).andExpect(status().isPreconditionRequired());
        mvc.perform(patch("/tasks/1").header("If-Match", "\"7\"").contentType(MediaType.valueOf("application/merge-patch+json")).content("{\"status\":\"done\"}")).andExpect(status().isPreconditionFailed());
        mvc.perform(patch("/tasks/1").header("If-Match", "\"0\"").contentType(MediaType.valueOf("application/merge-patch+json")).content("{\"status\":\"blocked\"}")).andExpect(status().isBadRequest());
    }
}
