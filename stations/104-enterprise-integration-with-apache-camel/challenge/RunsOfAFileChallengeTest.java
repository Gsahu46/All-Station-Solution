package com.bimaly.integration;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: the bank's support line asks "what happened to our file?" and knows only its name. */
class RunsOfAFileChallengeTest extends ApiTest {

    @Test
    void everyRunOfAFileIsListedOldestFirst() throws Exception {
        String file = HEADER + "KB-9101,Meera Iyer,1988-04-12,TERM10,1000000000\n";
        upload("KOSHBANK-20270101.csv", file);
        awaitRun("KOSHBANK-20270101.csv", Runs.Status.DONE);
        Thread.sleep(1_100);
        upload("KOSHBANK-20270101.csv", file);
        awaitRun("KOSHBANK-20270101.csv", Runs.Status.DUPLICATE);

        mvc.perform(get("/integration/runs").param("file", "KOSHBANK-20270101.csv")).andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[0].status").value("DONE")).andExpect(jsonPath("$[1].status").value("DUPLICATE"));
    }

    @Test
    void anUnknownFileHasNoRunsAndTheNameIsRequired() throws Exception {
        mvc.perform(get("/integration/runs").param("file", "KOSHBANK-19990101.csv")).andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(0));
        mvc.perform(get("/integration/runs")).andExpect(status().isBadRequest());
    }
}
