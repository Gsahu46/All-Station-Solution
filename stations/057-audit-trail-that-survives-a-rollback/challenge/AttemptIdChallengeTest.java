package com.tijori.transfers;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: a refused transfer's problem response carries "attemptId", the same id as its audit events, so a
 * customer reading it to support can be found in the trail at once.
 */
class AttemptIdChallengeTest extends ApiTest {

    @Test
    void theRefusalNamesItsAttempt() throws Exception {
        String body = transfer(2, 1, 500_000).andExpect(status().isUnprocessableContent()).andReturn().getResponse().getContentAsString();
        String attemptId = com.jayway.jsonpath.JsonPath.read(body, "$.attemptId");
        assertThat(jdbc.sql("SELECT event FROM audit_events WHERE attempt_id = ?::uuid ORDER BY id").param(attemptId).query(String.class).list())
                .containsExactly("TRANSFER_ATTEMPTED", "TRANSFER_FAILED");
    }
}
