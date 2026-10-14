package com.dakroute.tracking;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/** Shared setup: the whole app through MockMvc, filters included. */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    @Autowired
    MockMvc mvc;

    ResultActions track(String awb) throws Exception {
        return mvc.perform(get("/shipments/{awb}", awb));
    }

    ResultActions track(String awb, String requestId) throws Exception {
        return mvc.perform(get("/shipments/{awb}", awb).header("X-Request-Id", requestId));
    }
}
