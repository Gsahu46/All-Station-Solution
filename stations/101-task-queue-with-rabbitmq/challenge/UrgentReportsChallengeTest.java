package com.mediqo.reports;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: an emergency ward cannot wait behind the morning's routine reports. POST
 * /lab-reports/{id}/render?urgent=true sends the message with a higher priority, on a queue that supports priorities,
 * so it is the next one any worker takes.
 */
class UrgentReportsChallengeTest extends ApiTest {

    @Test
    void anUrgentReportJumpsTheQueue() throws Exception {
        render("LR-0401").andExpect(status().isAccepted());   // both workers busy for 2 s
        render("LR-0402").andExpect(status().isAccepted());
        for (String routine : new String[]{"LR-0201", "LR-0202", "LR-0203"}) {
            render(routine).andExpect(status().isAccepted());
        }
        mvc.perform(post("/lab-reports/LR-0005/render").param("urgent", "true")).andExpect(status().isAccepted());

        awaitStatus("LR-0005", "READY");
        // When the urgent one is done, none of the routine ones queued before it is.
        long routineDone = java.util.stream.Stream.of("LR-0201", "LR-0202", "LR-0203")
                .filter(id -> {
                    try {
                        return report(id).path("status").asString().equals("READY");
                    } catch (Exception e) {
                        throw new IllegalStateException(e);
                    }
                }).count();
        assertThat(routineDone).isZero();
    }
}
