package com.mediqo.reports;

import org.junit.jupiter.api.Test;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class DuplicateRenderReplayTest extends ApiTest {

    @Autowired
    RabbitTemplate template;

    @Test
    void theSameRequestTwiceIsOneMessageAndOneRender() throws Exception {
        render("LR-0011").andExpect(status().isAccepted());
        render("LR-0011").andExpect(status().isOk()).andExpect(jsonPath("$.status").value(org.hamcrest.Matchers.oneOf("QUEUED", "READY")));
        awaitStatus("LR-0011", "READY");
        render("LR-0011").andExpect(status().isOk()).andExpect(jsonPath("$.status").value("READY"));
        assertThat(worker.timesRendered("LR-0011")).isEqualTo(1);
    }

    @Test
    void aRepeatedMessageForARenderedReportIsSkipped() throws Exception {
        render("LR-0012").andExpect(status().isAccepted());
        awaitStatus("LR-0012", "READY");
        // The broker delivers it again (a redelivery after a lost acknowledgement looks the same to the worker).
        template.convertAndSend(ReportsApplication.EXCHANGE, ReportsApplication.ROUTING_KEY, new RenderWorker.RenderRequest("LR-0012"));
        await().atMost(Duration.ofSeconds(5)).until(() -> waiting(ReportsApplication.QUEUE) == 0);
        await().during(Duration.ofMillis(300)).until(() -> worker.timesRendered("LR-0012") == 1);
    }
}
