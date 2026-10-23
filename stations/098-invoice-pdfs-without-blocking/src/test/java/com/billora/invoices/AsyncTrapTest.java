package com.billora.invoices;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.task.TaskExecutionProperties;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Import;
import org.springframework.scheduling.annotation.Async;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Written first. */
@Import(AsyncTrapTest.OldWay.class)
class AsyncTrapTest extends ApiTest {

    /** The old way: @Async void, and the job is marked done at the end. If the render throws, the end never comes. */
    @TestConfiguration
    static class OldWay {
        private final Map<String, String> status = new ConcurrentHashMap<>();

        public String status(String invoiceId) {   // a method: the bean is an @Async proxy, its fields are not the real ones
            return status.get(invoiceId);
        }

        @Async
        public void render(String invoiceId) {
            status.put(invoiceId, "RUNNING");
            if (invoiceId.equals("INV-2026-0013")) {
                throw new IllegalStateException("The logo image of INV-2026-0013 is damaged.");   // to a log line, and nowhere else
            }
            status.put(invoiceId, "DONE");
        }
    }

    @Autowired
    OldWay oldWay;

    @Test
    void theDefaultPoolAcceptsEveryJobAndQueuesItWithoutLimit() throws Exception {
        // Spring Boot's own defaults for its application task executor: 8 threads, a queue with no limit.
        TaskExecutionProperties.Pool defaults = new TaskExecutionProperties().getPool();
        assertThat(defaults.getCoreSize()).isEqualTo(8);
        assertThat(defaults.getQueueCapacity()).isEqualTo(Integer.MAX_VALUE);

        ThreadPoolTaskExecutor likeTheDefault = new ThreadPoolTaskExecutor();
        likeTheDefault.setCorePoolSize(defaults.getCoreSize());
        likeTheDefault.setQueueCapacity(defaults.getQueueCapacity());
        likeTheDefault.initialize();
        CountDownLatch rendering = new CountDownLatch(1);
        try {
            for (int i = 0; i < 1000; i++) {   // a month-end rush: 1,000 people press "Download PDF"
                likeTheDefault.execute(() -> {
                    try {
                        rendering.await();
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                    }
                });
            }
            // Nobody is told "busy": 8 render, 992 wait in memory. At 40 s a render, the last one starts after about 83 minutes.
            assertThat(likeTheDefault.getActiveCount()).isEqualTo(8);
            assertThat(likeTheDefault.getQueueSize()).isEqualTo(992);
        } finally {
            rendering.countDown();
            likeTheDefault.shutdown();
        }
    }

    @Test
    void theOldWaySwallowsTheErrorAndTheApiReportsIt() throws Exception {
        oldWay.render("INV-2026-0013");
        await().during(Duration.ofMillis(500)).atMost(Duration.ofSeconds(2)).until(() -> "RUNNING".equals(oldWay.status("INV-2026-0013")));

        var job = awaitDone(location(start("INV-2026-0013").andExpect(status().isAccepted())));
        assertThat(job.at("/metadata/state").asString()).isEqualTo("FAILED");
        assertThat(job.at("/error/message").asString()).isEqualTo("The logo image of INV-2026-0013 is damaged.");
    }
}
