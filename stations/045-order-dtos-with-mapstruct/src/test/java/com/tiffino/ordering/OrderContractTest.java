package com.tiffino.ordering;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.json.JsonCompareMode;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: an order in, the same order out. LENIENT: every listed value is checked; fields added later may appear. */
class OrderContractTest extends ApiTest {

    static final String RESPONSE = """
            {"id":1,"customerName":"Asha Verma","phone":"******3210",
             "address":{"line":"Flat 4B, Lotus Residency, Baner Road","city":"Pune","pincode":"411045"},
             "deliveryInstructions":"Ring twice, baby sleeping",
             "lines":[{"item":"Paneer thali","quantity":2,"unitPricePaise":24900,"linePaise":49800},
                      {"item":"Masala chaas","quantity":1,"unitPricePaise":4900,"linePaise":4900}],
             "totalPaise":54700,"status":"PLACED"}""";

    @Test
    void anOrderComesBackWithEveryField() throws Exception {
        place(ORDER).andExpect(status().isCreated()).andExpect(header().string("Location", "/orders/1"))
                .andExpect(content().json(RESPONSE, JsonCompareMode.LENIENT));
        mvc.perform(get("/orders/1")).andExpect(status().isOk()).andExpect(content().json(RESPONSE, JsonCompareMode.LENIENT));
    }

    @Test
    void instructionsAreOptional() throws Exception {
        place(ORDER.replace("\"deliveryInstructions\":\"Ring twice, baby sleeping\",", ""))
                .andExpect(status().isCreated()).andExpect(jsonPath("$.deliveryInstructions").doesNotExist());
    }

    @Test
    void anUnknownOrderIs404() throws Exception {
        mvc.perform(get("/orders/99")).andExpect(status().isNotFound()).andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
    }

    @Test
    void badOrdersAre400() throws Exception {
        place(ORDER.replace("411045", "41104")).andExpect(status().isBadRequest());
        place(ORDER.replace("\"quantity\":2", "\"quantity\":0")).andExpect(status().isBadRequest());
        place(ORDER.replace("9876543210", "12345")).andExpect(status().isBadRequest());
        place(ORDER.replaceAll("\"lines\":\\[.*]", "\"lines\":[]")).andExpect(status().isBadRequest());
        place(ORDER.replace("\"customerName\"", "\"totalPaise\":1,\"customerName\"")).andExpect(status().isBadRequest());   // the client never sets the total
    }
}
