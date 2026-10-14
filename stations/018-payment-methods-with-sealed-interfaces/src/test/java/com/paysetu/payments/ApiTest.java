package com.paysetu.payments;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app through MockMvc, and a helper that pays ₹499 for order ORD-1 with a given method. */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    @Autowired
    MockMvc mvc;

    ResultActions intent(String methodJson) throws Exception {
        return intent(49_900, methodJson);
    }

    ResultActions intent(long amountPaise, String methodJson) throws Exception {
        return mvc.perform(post("/payment-intents").contentType(MediaType.APPLICATION_JSON).content(
                "{\"orderId\":\"ORD-1\",\"amountPaise\":" + amountPaise + ",\"method\":" + methodJson + "}"));
    }
}
