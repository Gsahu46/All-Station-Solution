package com.tiffino.orders;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: who may make which move. X-Actor stands in for real sign-in in this demo. Kitchens accept, reject,
 * prepare, mark ready and may cancel; riders pick up and deliver; customers may only cancel. A move by the wrong
 * party is 403; a move the table forbids is still 409.
 */
class WhoMayMoveChallengeTest extends ApiTest {

    ResultActions as(String actor, long id, String to) throws Exception {
        var request = post("/orders/{id}/status-changes", id).contentType(MediaType.APPLICATION_JSON).content("{\"to\":\"" + to + "\"}");
        return mvc.perform(actor == null ? request : request.header("X-Actor", actor));
    }

    @Test
    void eachPartyMakesOnlyItsOwnMoves() throws Exception {
        as("RIDER", 1001, "ACCEPTED").andExpect(status().isForbidden());
        as("CUSTOMER", 1001, "ACCEPTED").andExpect(status().isForbidden());
        as("RESTAURANT", 1001, "ACCEPTED").andExpect(status().isOk());
        as("RESTAURANT", 1003, "READY_FOR_PICKUP").andExpect(status().isOk());
        as("RESTAURANT", 1003, "PICKED_UP").andExpect(status().isForbidden());
        as("RIDER", 1003, "PICKED_UP").andExpect(status().isOk());
    }

    @Test
    void theTableStillWinsAndAnActorIsRequired() throws Exception {
        as("CUSTOMER", 1003, "CANCELLED").andExpect(status().isConflict());   // too late to cancel: it is being prepared
        as(null, 1001, "ACCEPTED").andExpect(status().isBadRequest());
        as("CHEF", 1001, "ACCEPTED").andExpect(status().isBadRequest());
    }
}
