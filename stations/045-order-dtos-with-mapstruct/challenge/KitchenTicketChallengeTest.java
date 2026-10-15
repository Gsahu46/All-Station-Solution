package com.tiffino.ordering;

import org.junit.jupiter.api.Test;
import org.springframework.test.json.JsonCompareMode;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /orders/{id}/kitchen-ticket for the kitchen screen: the order id, each line as "2 x Paneer thali",
 * and the instructions. No customer name, phone, address or prices: the kitchen does not need them. A second MapStruct
 * method, with a custom mapping for the lines.
 */
class KitchenTicketChallengeTest extends ApiTest {

    @Test
    void theTicketHasOnlyWhatTheKitchenNeeds() throws Exception {
        place(ORDER);
        mvc.perform(get("/orders/1/kitchen-ticket")).andExpect(status().isOk()).andExpect(content().json("""
                {"orderId":1,"items":["2 x Paneer thali","1 x Masala chaas"],"instructions":"Ring twice, baby sleeping"}""", JsonCompareMode.STRICT));
        mvc.perform(get("/orders/9/kitchen-ticket")).andExpect(status().isNotFound());
    }
}
