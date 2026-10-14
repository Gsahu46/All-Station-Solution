package com.tiffino.orders;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app through MockMvc, the demo orders fresh before each test. */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    Orders orders;

    @BeforeEach
    void freshOrders() {
        orders.reset();
    }

    /** Sends the move as the party that would make it: riders pick up and deliver, customers cancel, kitchens do the rest. */
    ResultActions change(long id, String to) throws Exception {
        String actor = switch (to) {
            case "PICKED_UP", "DELIVERED" -> "RIDER";
            case "CANCELLED" -> "CUSTOMER";
            default -> "RESTAURANT";
        };
        return mvc.perform(post("/orders/{id}/status-changes", id).header("X-Actor", actor)
                .contentType(MediaType.APPLICATION_JSON).content("{\"to\":\"" + to + "\"}"));
    }
}
