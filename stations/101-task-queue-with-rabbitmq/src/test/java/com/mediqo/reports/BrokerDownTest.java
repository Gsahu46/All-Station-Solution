package com.mediqo.reports;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** No broker at all (nothing listens on port 1): the API says so instead of answering 202 for a message it does not have. */
@SpringBootTest(properties = {"spring.rabbitmq.port=1", "mediqo.reports.dir=target/test-reports-broker-down"})
@AutoConfigureMockMvc
class BrokerDownTest {

    @Autowired
    MockMvc mvc;

    @Test
    void withoutTheBrokerItIs503AndTheRequestCanBeTriedAgain() throws Exception {
        mvc.perform(post("/lab-reports/LR-0009/render")).andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.detail").value("The render queue is not reachable. Try again shortly."));
        mvc.perform(post("/lab-reports/LR-0009/render")).andExpect(status().isServiceUnavailable());   // not "already queued"
    }
}
