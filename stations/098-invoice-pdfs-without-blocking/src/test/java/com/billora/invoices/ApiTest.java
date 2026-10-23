package com.billora.invoices;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.time.Duration;

import static org.awaitility.Awaitility.await;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * Shared setup: the whole app, rendering 5 ms a page (a 300-page invoice in 1.5 s, not 40 s), two workers and a queue
 * of three, so a full pool is easy to reach. Waiting is done with Awaitility: it polls until true or fails, never a fixed sleep.
 */
@SpringBootTest(properties = {"billora.pdf.ms-per-page=5", "billora.pdf.workers=2", "billora.pdf.queue=3"})
@AutoConfigureMockMvc
abstract class ApiTest {

    static final JsonMapper JSON = JsonMapper.builder().build();

    @Autowired
    MockMvc mvc;
    @Autowired
    ThreadPoolTaskExecutor pdfExecutor;

    ResultActions start(String invoiceId) throws Exception {
        return mvc.perform(post("/invoices/{id}/pdf-jobs", invoiceId));
    }

    JsonNode job(String path) throws Exception {
        return JSON.readTree(mvc.perform(get(path)).andReturn().getResponse().getContentAsString());
    }

    /** Polls the job every 20 ms until it is done, at most 10 s. */
    JsonNode awaitDone(String path) {
        return await().atMost(Duration.ofSeconds(10)).pollInterval(Duration.ofMillis(20)).until(() -> job(path), j -> j.get("done").asBoolean());
    }

    void awaitIdlePool() {
        await().atMost(Duration.ofSeconds(20)).until(() -> pdfExecutor.getActiveCount() == 0 && pdfExecutor.getQueueSize() == 0);
    }

    static String location(ResultActions result) {
        return result.andReturn().getResponse().getHeader("Location");
    }
}
