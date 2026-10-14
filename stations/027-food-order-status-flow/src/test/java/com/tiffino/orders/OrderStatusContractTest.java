package com.tiffino.orders;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: the whole happy path, a double tap, a refused move, and bad requests. */
class OrderStatusContractTest extends ApiTest {

    @Test
    void anOrderGoesFromPlacedToDeliveredOneStepAtATime() throws Exception {
        for (String to : new String[]{"ACCEPTED", "PREPARING", "READY_FOR_PICKUP", "PICKED_UP"}) {
            change(1001, to).andExpect(status().isOk()).andExpect(jsonPath("$.status").value(to));
        }
        change(1001, "DELIVERED").andExpect(jsonPath("$.status").value("DELIVERED"))
                .andExpect(jsonPath("$.history", hasSize(6)))
                .andExpect(jsonPath("$.history[0].status").value("PLACED"))
                .andExpect(jsonPath("$.history[5].status").value("DELIVERED"));
        mvc.perform(get("/orders/1001")).andExpect(status().isOk()).andExpect(jsonPath("$.status").value("DELIVERED"));
    }

    @Test
    void aDoubleTapIsNotAnErrorAndNotASecondStep() throws Exception {
        change(1003, "READY_FOR_PICKUP").andExpect(jsonPath("$.history", hasSize(4)));
        change(1003, "READY_FOR_PICKUP").andExpect(status().isOk()).andExpect(jsonPath("$.history", hasSize(4)));
    }

    @Test
    void aRefusedMoveSaysWhatIsAllowed() throws Exception {
        change(1003, "DELIVERED")
                .andExpect(status().isConflict())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.currentStatus").value("PREPARING"))
                .andExpect(jsonPath("$.allowedNext[0]").value("READY_FOR_PICKUP"));
        mvc.perform(get("/orders/1003")).andExpect(jsonPath("$.status").value("PREPARING"));   // nothing changed
    }

    @Test
    void anUnknownOrderIs404() throws Exception {
        mvc.perform(get("/orders/9999")).andExpect(status().isNotFound()).andExpect(jsonPath("$.title").value("Order not found"));
        change(9999, "ACCEPTED").andExpect(status().isNotFound());
    }

    @Test
    void anUnknownStatusOrNoStatusIs400() throws Exception {
        change(1001, "TELEPORTED").andExpect(status().isBadRequest());
        change(1001, "accepted").andExpect(status().isBadRequest());   // statuses are exact names
        mvc.perform(post("/orders/1001/status-changes").contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isBadRequest());
        mvc.perform(get("/orders/abc")).andExpect(status().isBadRequest());
    }
}
