package com.taskloom.support;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: the escaping keeps a message from closing the tag, but a model may still follow words in it. Warn the
 * agent that a summary was made from text that looks like instructions to a model, so they read the ticket themselves.
 */
class InjectionWarningChallengeTest extends ApiTest {

    @Test
    void textThatLooksLikeInstructionsIsFlaggedWithItsMessageNumber() throws Exception {
        summary("T-1003", "priya").andExpect(status().isOk())
                .andExpect(jsonPath("$.warnings.length()").value(1))
                .andExpect(jsonPath("$.warnings[0]").value("Message 2 contains text that looks like instructions to an AI model. Read the ticket before acting on the summary."));
    }

    @Test
    void anOrdinaryTicketHasNoWarnings() throws Exception {
        summary("T-1001", "priya").andExpect(status().isOk()).andExpect(jsonPath("$.warnings").isEmpty());
    }
}
