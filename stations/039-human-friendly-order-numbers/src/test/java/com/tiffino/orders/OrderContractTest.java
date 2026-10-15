package com.tiffino.orders;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: placing an order, and finding it the way a customer reads the number out. */
class OrderContractTest extends ApiTest {

    @Test
    void anOrderGetsAReadableNumberAndALocation() throws Exception {
        String body = place("""
                {"outletId":"tf-07","totalPaise":45000}""")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.orderNumber").value(org.hamcrest.Matchers.matchesPattern(ORDER_NUMBER)))
                .andExpect(jsonPath("$.outletId").value("TF-07"))
                .andExpect(header().string("Location", org.hamcrest.Matchers.startsWith("/orders/by-number/TF-")))
                .andReturn().getResponse().getContentAsString();
        String number = body.replaceAll(".*\"orderNumber\":\"([^\"]+)\".*", "$1");
        lookUp(number).andExpect(status().isOk()).andExpect(jsonPath("$.totalPaise").value(45000));
        lookUp(number.toLowerCase(java.util.Locale.ROOT).replace("-", " ")).andExpect(status().isOk())
                .andExpect(jsonPath("$.orderNumber").value(number));
    }

    @Test
    void aMistypedDigitIs400BeforeAnyLookup() throws Exception {
        String number = store.place("TF-07", 45_000).orderNumber();
        char wrong = number.charAt(6) == '9' ? '8' : (char) (number.charAt(6) + 1);
        lookUp(number.substring(0, 6) + wrong + number.substring(7)).andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.title").value("Check the order number"));
    }

    @Test
    void aValidNumberNobodyHasIs404() throws Exception {
        lookUp(validNumber(9_999_999)).andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
    }

    @Test
    void somethingThatIsNotAnOrderNumberIs400() throws Exception {
        lookUp("12345").andExpect(status().isBadRequest()).andExpect(jsonPath("$.title").value("Not an order number"));
        lookUp("f47ac10b-58cc-4372-a567-0e02b2c3d479").andExpect(status().isBadRequest());
    }

    @Test
    void badOrdersAre400() throws Exception {
        place("""
                {"outletId":"Koramangala","totalPaise":45000}""").andExpect(status().isBadRequest());
        place("""
                {"outletId":"TF-07","totalPaise":0}""").andExpect(status().isBadRequest());
        place("""
                {"outletId":"TF-07","totalPaise":45000,"orderNumber":"TF-1000001-8"}""").andExpect(status().isBadRequest());
    }
}
