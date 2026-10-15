package com.kartwala.refunds;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup. Refunds change the ledger, so every test method gets a fresh app. */
@SpringBootTest
@AutoConfigureMockMvc
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_EACH_TEST_METHOD)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;

    ResultActions refund(String json, String requestId) throws Exception {
        var request = post("/refunds").contentType(MediaType.APPLICATION_JSON).content(json);
        return mvc.perform(requestId == null ? request : request.header("X-Request-Id", requestId));
    }

    ResultActions refund(String json) throws Exception {
        return refund(json, null);
    }
}
