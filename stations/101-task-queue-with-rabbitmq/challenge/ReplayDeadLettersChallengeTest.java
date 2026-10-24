package com.mediqo.reports;

import org.junit.jupiter.api.Test;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;

import java.time.Duration;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: POST /dead-letters/replay moves every parked message back to the work queue (after someone fixed the
 * cause) and answers how many it moved. The report goes back to QUEUED. Here the scan is still damaged, so it fails
 * again and is parked again.
 */
class ReplayDeadLettersChallengeTest extends ApiTest {

    @Autowired
    RabbitTemplate template;

    @Test
    void parkedMessagesGoBackToTheWorkQueue() throws Exception {
        render("LR-0013").andExpect(status().isAccepted());
        awaitStatus("LR-0013", "FAILED");
        await().atMost(Duration.ofSeconds(5)).until(() -> waiting(ReportsApplication.DEAD_LETTER_QUEUE) == 1);

        mvc.perform(post("/dead-letters/replay")).andExpect(status().isOk()).andExpect(jsonPath("$.moved").value(1));
        assertThat(waiting(ReportsApplication.DEAD_LETTER_QUEUE)).isZero();

        awaitStatus("LR-0013", "FAILED");   // failed again, after three more tries
        await().atMost(Duration.ofSeconds(5)).until(() -> waiting(ReportsApplication.DEAD_LETTER_QUEUE) == 1);
        Message parked = template.receive(ReportsApplication.DEAD_LETTER_QUEUE, 1_000);
        @SuppressWarnings("unchecked")
        Map<String, Object> death = ((List<Map<String, Object>>) parked.getMessageProperties().getHeaders().get("x-death")).getFirst();
        // RabbitMQ 4 does not take x-death from a message a client publishes: its history starts again at 1.
        // Found while building; keep your own count in a header if you need one.
        assertThat(((Number) death.get("count")).longValue()).isEqualTo(1);
    }

    @Test
    void nothingParkedMovesNothing() throws Exception {
        mvc.perform(post("/dead-letters/replay")).andExpect(status().isOk()).andExpect(jsonPath("$.moved").value(0));
    }
}
