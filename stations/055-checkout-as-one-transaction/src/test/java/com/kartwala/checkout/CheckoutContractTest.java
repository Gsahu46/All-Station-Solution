package com.kartwala.checkout;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The HTTP contract: checkout and read it back; valid, invalid and not found. */
class CheckoutContractTest extends ApiTest {

    @Test
    void aCheckoutReservesStockAndRecordsThePayment() throws Exception {
        String url = checkout("[{\"productId\":1,\"quantity\":2},{\"productId\":2,\"quantity\":5}]").andExpect(status().isCreated())
                .andExpect(content().json("""
                        {"customerId":7,"totalPaise":134300,"payment":{"status":"CAPTURED","amountPaise":134300},"lines":[
                         {"productId":1,"name":"Assam tea, 500 g","quantity":2,"unitPricePaise":34900},
                         {"productId":2,"name":"Kashmiri chilli, 100 g","quantity":5,"unitPricePaise":12900}]}"""))
                .andReturn().getResponse().getHeader("Location");
        assertThat(state()).isEqualTo("1/2/1/48/0");   // the last 5 chilli packets are now this order's
        mvc.perform(get(url)).andExpect(status().isOk()).andExpect(jsonPath("$.totalPaise").value(134300))
                .andExpect(jsonPath("$.lines.length()").value(2));
    }

    @Test
    void outOfStockIs409AndNothingIsKept() throws Exception {
        checkout("[{\"productId\":1,\"quantity\":2},{\"productId\":3,\"quantity\":1}]").andExpect(status().isConflict())
                .andExpect(jsonPath("$.detail").value("Not enough \"Steel tiffin box\" for 1."));
        assertThat(state()).isEqualTo("0/0/0/50/5");
    }

    @Test
    void unknownOrRepeatedProductsAre422() throws Exception {
        checkout("[{\"productId\":99,\"quantity\":1}]").andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.title").value("Unknown product"));
        checkout("[{\"productId\":1,\"quantity\":1},{\"productId\":1,\"quantity\":2}]").andExpect(status().isUnprocessableContent());
        assertThat(state()).isEqualTo("0/0/0/50/5");
    }

    @Test
    void malformedCheckoutsAre400() throws Exception {
        checkout("[]").andExpect(status().isBadRequest());
        checkout("[{\"productId\":1,\"quantity\":0}]").andExpect(status().isBadRequest());
        checkout("[{\"productId\":1,\"quantity\":11}]").andExpect(status().isBadRequest());
        checkout("[{\"productId\":1,\"quantity\":1.5}]").andExpect(status().isBadRequest());
        checkout("[{\"quantity\":1}]").andExpect(status().isBadRequest());
        mvc.perform(post("/checkouts").contentType(MediaType.APPLICATION_JSON).content("{\"lines\":[{\"productId\":1,\"quantity\":1}]}"))
                .andExpect(status().isBadRequest());
        assertThat(state()).isEqualTo("0/0/0/50/5");
    }

    @Test
    void unknownCheckoutsAre404() throws Exception {
        mvc.perform(get("/checkouts/99")).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No checkout 99."));
    }
}
