package com.taskloom.board;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: DELETE /tasks/{id} with If-Match: 204 if the task is still the version you saw, 412 if someone changed
 * it since (you may be deleting their note), 428 without If-Match.
 */
class ConditionalDeleteChallengeTest extends ApiTest {

    @Test
    void deleteTheVersionYouSaw() throws Exception {
        mvc.perform(delete("/tasks/2").header("If-Match", etag(2))).andExpect(status().isNoContent());
        read(2).andExpect(status().isNotFound());
    }

    @Test
    void notAVersionSomeoneHasChangedSince() throws Exception {
        String seen = etag(1);
        edit(1, seen, body("Write the press release", "doing", "asha"));
        mvc.perform(delete("/tasks/1").header("If-Match", seen)).andExpect(status().isPreconditionFailed());
        mvc.perform(delete("/tasks/1")).andExpect(status().isPreconditionRequired());
        read(1).andExpect(status().isOk());
    }
}
