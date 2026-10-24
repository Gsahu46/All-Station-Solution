package com.mediqo.reports;

import org.junit.jupiter.api.Test;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import tools.jackson.databind.JsonNode;

import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Base64;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class RetryAndDeadLetterMessagingTest extends ApiTest {

    @Autowired
    RabbitTemplate template;

    @Test
    void aBusyLabSystemIsRetriedAndTheReportIsRendered() throws Exception {
        render("LR-0042").andExpect(status().isAccepted());   // the lab system does not answer the first time
        awaitStatus("LR-0042", "READY");
        assertThat(worker.timesRendered("LR-0042")).isEqualTo(1);
        assertThat(waiting(ReportsApplication.DEAD_LETTER_QUEUE)).isZero();
    }

    @Test
    void aDamagedReportEndsInTheDeadLetterQueueWithItsReason() throws Exception {
        render("LR-0013").andExpect(status().isAccepted());
        var failed = awaitStatus("LR-0013", "FAILED");
        assertThat(failed.path("failure").asString()).isEqualTo("The scan of LR-0013 is damaged.");
        await().atMost(Duration.ofSeconds(5)).until(() -> waiting(ReportsApplication.DEAD_LETTER_QUEUE) == 1);
        Message parked = template.receive(ReportsApplication.DEAD_LETTER_QUEUE, 1_000);
        assertThat(new String(parked.getBody(), StandardCharsets.UTF_8)).isEqualTo("{\"reportId\":\"LR-0013\"}");
        @SuppressWarnings("unchecked")
        Map<String, Object> death = ((List<Map<String, Object>>) parked.getMessageProperties().getHeaders().get("x-death")).getFirst();
        assertThat(death).containsEntry("reason", "rejected").containsEntry("queue", ReportsApplication.QUEUE);
        assertThat(waiting(ReportsApplication.QUEUE)).isZero();   // not retried for ever
    }

    /** The broker's own view of a worker dying: its connection closed from the broker's side, mid-render. */
    @Test
    void aWorkerCutOffMidRenderLosesNothing() throws Exception {
        // The management API lists connections a few seconds late: find the app's before the render starts.
        JsonNode connections = await().atMost(Duration.ofSeconds(15)).until(() -> management("GET", "/api/connections"), list -> !list.isEmpty());
        render("LR-0500").andExpect(status().isAccepted());   // 500 pages: 2.5 s here
        // A worker has it and is not done: nothing waiting in the queue, and no PDF yet. (Prefetch 1: it holds just this one.)
        await().atMost(Duration.ofSeconds(2)).until(() -> waiting(ReportsApplication.QUEUE) == 0);
        assertThat(report("LR-0500").path("status").asString()).isEqualTo("QUEUED");
        for (JsonNode connection : connections) {
            management("DELETE", "/api/connections/" + URLEncoder.encode(connection.path("name").asString(), StandardCharsets.UTF_8).replace("+", "%20"));
        }
        awaitStatus("LR-0500", "READY");
        await().atMost(Duration.ofSeconds(10)).until(() -> waiting(ReportsApplication.QUEUE) == 0);
        assertThat(worker.timesRendered("LR-0500")).isEqualTo(1);   // the cut-off worker stopped; the next one rendered it
    }

    JsonNode management(String method, String path) throws Exception {
        HttpRequest request = HttpRequest.newBuilder(URI.create(rabbit.getHttpUrl() + path))
                .header("Authorization", "Basic " + Base64.getEncoder().encodeToString("guest:guest".getBytes()))
                .method(method, HttpRequest.BodyPublishers.noBody()).build();
        try (HttpClient http = HttpClient.newHttpClient()) {
            String body = http.send(request, HttpResponse.BodyHandlers.ofString()).body();
            return body.isBlank() ? JSON.createObjectNode() : JSON.readTree(body);
        }
    }
}
