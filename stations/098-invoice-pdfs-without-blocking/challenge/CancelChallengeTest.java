package com.billora.invoices;

import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: POST /pdf-jobs/{jobId}:cancel, AIP-151's custom method. A queued job is cancelled at once and never
 * renders; a running one stops after its current page. Either ends done, with the error code CANCELLED.
 */
class CancelChallengeTest extends ApiTest {

    @Test
    void aRunningJobStopsAfterItsCurrentPage() throws Exception {
        awaitIdlePool();
        String path = location(start("INV-2026-0300"));
        await().atMost(Duration.ofSeconds(5)).until(() -> job(path).at("/metadata/pagesDone").asInt() > 10);
        mvc.perform(post(path + ":cancel")).andExpect(status().isOk());
        var cancelled = awaitDone(path);
        assertThat(cancelled.at("/metadata/state").asString()).isEqualTo("CANCELLED");
        assertThat(cancelled.at("/error/code").asString()).isEqualTo("CANCELLED");
        assertThat(cancelled.at("/metadata/pagesDone").asInt()).isLessThan(300);
        mvc.perform(post(path + ":cancel")).andExpect(status().isConflict());   // already done
    }

    @Test
    void aQueuedJobIsCancelledAtOnceAndNeverRuns() throws Exception {
        awaitIdlePool();
        String a = location(start("INV-2026-0301"));
        String b = location(start("INV-2026-0302"));
        String queued = location(start("INV-2026-0303"));   // both workers busy: this one waits
        mvc.perform(post(queued + ":cancel")).andExpect(status().isOk()).andExpect(jsonPath("$.done").value(true))
                .andExpect(jsonPath("$.metadata.state").value("CANCELLED"));
        awaitDone(a);
        awaitDone(b);
        awaitIdlePool();
        assertThat(job(queued).at("/metadata/pagesDone").asInt()).isZero();
        mvc.perform(post("/pdf-jobs/" + UUID.randomUUID() + ":cancel")).andExpect(status().isNotFound());
    }
}
