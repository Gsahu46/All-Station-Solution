package com.taskloom.support;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static com.taskloom.support.TestModel.MODEL;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** The whole app against the simulated model, which gets 1 s to answer (20 s in production). */
@SpringBootTest(properties = "taskloom.model.timeout=1s")
@AutoConfigureMockMvc
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    Tickets tickets;
    @Autowired
    Summaries summaries;

    @DynamicPropertySource
    static void model(DynamicPropertyRegistry registry) {
        registry.add("taskloom.model.url", MODEL::url);
    }

    @BeforeEach
    void freshModel() {
        MODEL.reset();
        summaries.forgetAll();
    }

    ResultActions summary(String ticket, String user) throws Exception {
        return mvc.perform(post("/tickets/{id}/summary", ticket).with(httpBasic(user, user + "-demo-pass")));
    }

    /** What the app sent as the thread in its last request. */
    static String sentThread() {
        return MODEL.last().path("messages").get(0).path("content").asString();
    }
}
