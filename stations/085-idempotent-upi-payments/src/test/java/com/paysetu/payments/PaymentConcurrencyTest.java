package com.paysetu.payments;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The invariant under real parallel HTTP requests: one key, one payment.
 * A single-threaded replay test cannot catch a check-then-insert race; this one can.
 */
class PaymentConcurrencyTest extends ApiTest {

    private static final int REQUESTS = 20;

    @Test
    void twentyParallelRetriesWithTheSameKeyCreateOnePayment() throws Exception {
        List<String> bodies = fireTogether(i -> "same-key-burst-01");

        assertThat(paymentCount()).isEqualTo(1);
        assertThat(bodies).hasSize(REQUESTS).containsOnly(bodies.getFirst()); // everyone got the same paymentId
    }

    @Test
    void twentyParallelPaymentsWithDifferentKeysAllGoThrough() throws Exception {
        List<String> bodies = fireTogether(i -> "different-key-" + i);

        assertThat(paymentCount()).isEqualTo(REQUESTS);
        assertThat(bodies).doesNotHaveDuplicates();
    }

    private List<String> fireTogether(java.util.function.IntFunction<String> keyFor) throws Exception {
        CountDownLatch startGate = new CountDownLatch(1);
        List<Future<String>> results = new ArrayList<>();
        try (var pool = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < REQUESTS; i++) {
                String key = keyFor.apply(i);
                results.add(pool.submit(() -> {
                    startGate.await(); // all threads wait here, then hit the API at the same moment
                    return pay(key, ASHA_PAYS_RAVI).expectStatus().isCreated()
                            .expectBody(String.class).returnResult().getResponseBody();
                }));
            }
            startGate.countDown();
            List<String> bodies = new ArrayList<>();
            for (Future<String> f : results) {
                bodies.add(f.get());
            }
            return bodies;
        }
    }
}
