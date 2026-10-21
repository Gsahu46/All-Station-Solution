package com.taskloom.board;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class TaskContractTest extends ApiTest {

    @Test
    void aTaskComesWithItsVersionAsETag() throws Exception {
        read(1).andExpect(status().isOk()).andExpect(header().string("ETag", "\"0\""))
                .andExpect(jsonPath("$.title").value("Write the press release")).andExpect(jsonPath("$.version").value(0));
    }

    @Test
    void anEditWithTheETagSavesAndGivesTheNextETag() throws Exception {
        edit(1, "\"0\"", body("  Write the press release ", "doing", "asha")).andExpect(status().isOk())
                .andExpect(header().string("ETag", "\"1\"")).andExpect(jsonPath("$.status").value("doing")).andExpect(jsonPath("$.title").value("Write the press release"));
        read(1).andExpect(header().string("ETag", "\"1\""));
    }

    /** Spring MVC answers If-None-Match for a ResponseEntity that carries an ETag: a board polling for changes gets 304. */
    @Test
    void anUnchangedTaskIs304ForAPollingBoard() throws Exception {
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get("/tasks/1").header("If-None-Match", "\"0\""))
                .andExpect(status().isNotModified()).andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.content().string(""));
        edit(1, "\"0\"", body("Write the press release", "doing", "asha"));
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get("/tasks/1").header("If-None-Match", "\"0\""))
                .andExpect(status().isOk()).andExpect(header().string("ETag", "\"1\""));
    }

    @Test
    void anUnknownTaskIs404() throws Exception {
        read(99).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No such task"));
        edit(99, "\"0\"", body("X", "open", "asha")).andExpect(status().isNotFound());
    }

    @Test
    void anEditWithoutIfMatchIs428() throws Exception {
        edit(1, null, body("Write the press release", "doing", "asha")).andExpect(status().isPreconditionRequired())
                .andExpect(jsonPath("$.detail").value("Send If-Match with the ETag from GET /tasks/1"));
    }

    @Test
    void aTitleAlreadyOnTheBoardIs409NotA412() throws Exception {
        // The ETag is right, so this is not a stale copy: the edit itself clashes with the board.
        edit(1, etag(1), body("Book the venue", "open", "asha")).andExpect(status().isConflict())
                .andExpect(jsonPath("$.detail").value("A task with this title is already on the board"));
        read(1).andExpect(header().string("ETag", "\"0\""));
    }

    @Test
    void badBodiesAre400() throws Exception {
        edit(1, "\"0\"", body("", "open", "asha")).andExpect(status().isBadRequest());
        edit(1, "\"0\"", body("Write the press release", "blocked", "asha")).andExpect(status().isBadRequest());
        edit(1, "\"0\"", "{\"title\":\"x\"}").andExpect(status().isBadRequest());
    }
}
