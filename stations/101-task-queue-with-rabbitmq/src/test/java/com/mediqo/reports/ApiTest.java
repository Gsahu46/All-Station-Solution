package com.mediqo.reports;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.amqp.rabbit.core.RabbitAdmin;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.testcontainers.rabbitmq.RabbitMQContainer;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.Comparator;
import java.util.stream.Stream;

import static org.awaitility.Awaitility.await;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * The whole app and a real RabbitMQ. Pages take 5 ms (20 ms in production) and retries wait 100 ms, then 200 ms
 * (1 s, 2 s). Each test starts with empty queues and no report files; each uses its own report ids.
 */
@SpringBootTest(properties = {"mediqo.reports.dir=target/test-reports", "mediqo.reports.ms-per-page=5",
        "spring.rabbitmq.listener.simple.retry.initial-interval=100ms"})
@AutoConfigureMockMvc
@Import(RabbitTestConfig.class)
abstract class ApiTest {

    static final JsonMapper JSON = JsonMapper.builder().build();

    @Autowired
    MockMvc mvc;
    @Autowired
    RabbitAdmin admin;
    @Autowired
    RabbitMQContainer rabbit;
    @Autowired
    RenderWorker worker;

    @BeforeEach
    void emptyQueuesAndNoFiles() throws IOException {
        admin.purgeQueue(ReportsApplication.QUEUE);
        admin.purgeQueue(ReportsApplication.DEAD_LETTER_QUEUE);
        try (Stream<Path> files = Files.list(Path.of("target/test-reports"))) {
            files.sorted(Comparator.reverseOrder()).forEach(f -> f.toFile().delete());
        }
    }

    ResultActions render(String id) throws Exception {
        return mvc.perform(post("/lab-reports/{id}/render", id));
    }

    JsonNode report(String id) throws Exception {
        return JSON.readTree(mvc.perform(get("/lab-reports/{id}", id)).andReturn().getResponse().getContentAsString());
    }

    JsonNode awaitStatus(String id, String status) {
        return await().atMost(Duration.ofSeconds(15)).pollInterval(Duration.ofMillis(50))
                .until(() -> report(id), r -> status.equals(r.path("status").asString()));
    }

    long waiting(String queue) {
        return admin.getQueueInfo(queue).getMessageCount();
    }
}
