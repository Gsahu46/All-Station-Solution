package com.billora.invoices;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: tell the client when to look again. While a job is not done, its answers carry Retry-After: the
 * seconds the pages left should take (rounded up, at least 1). A done job has none: there is nothing to wait for.
 */
class RetryAfterChallengeTest extends ApiTest {

    @Test
    void anUnfinishedJobSaysWhenToLookAgain() throws Exception {
        awaitIdlePool();
        var started = start("INV-2026-0300").andExpect(status().isAccepted()).andExpect(header().string("Retry-After", "2"));   // 300 x 5 ms
        String path = location(started);
        awaitDone(path);
        mvc.perform(get(path)).andExpect(status().isOk()).andExpect(header().doesNotExist("Retry-After"));
    }

    @Test
    void aSmallJobSaysOneSecond() throws Exception {
        awaitIdlePool();
        String path = location(start("INV-2026-0003").andExpect(header().string("Retry-After", "1")));
        awaitDone(path);
    }
}
