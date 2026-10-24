package com.seatsure.sales;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.TestPropertySource;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static com.seatsure.sales.TestGateway.GATEWAY;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: no connection is held while the gateway thinks, but a request thread still is. A bulkhead lets at
 * most seatsure.payments.max-concurrent charges wait on the gateway (4 in this test); the next order is refused at
 * once with 503, and its seats are given back, instead of one more thread hanging for the full timeout.
 */
@TestPropertySource(properties = "seatsure.payments.max-concurrent=4")
class GatewayBulkheadChallengeTest extends ApiTest {

    @Test
    void beyondTheLimitOrdersAreRefusedAtOnce() throws Exception {
        GATEWAY.delayMillis = 3_000;   // hangs past the 1 s limit
        CountDownLatch open = new CountDownLatch(1);
        List<Future<Integer>> fans = new ArrayList<>();
        try (var threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 8; i++) {
                fans.add(threads.submit(() -> {
                    open.await();
                    return order(1, "fan", 1).andReturn().getResponse().getStatus();
                }));
            }
            open.countDown();
        }
        assertThat(fans).extracting(Future::resultNow).filteredOn(s -> s == 504).hasSize(4);
        assertThat(fans).extracting(Future::resultNow).filteredOn(s -> s == 503).hasSize(4);
        assertThat(GATEWAY.idempotencyKeys).hasSize(4);   // the refused four never reached the gateway
        assertThat(sold(1)).isZero();

        GATEWAY.delayMillis = 0;
        order(1, "fan", 1).andExpect(status().isCreated());   // places freed again
    }
}
