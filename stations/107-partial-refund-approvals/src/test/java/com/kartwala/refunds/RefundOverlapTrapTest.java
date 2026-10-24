package com.kartwala.refunds;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The mixer cost ₹4,999. Twenty agents, each answering a call from the same angry customer, refund ₹1,000 at the same
 * moment. Written first.
 */
class RefundOverlapTrapTest extends ApiTest {

    @Autowired
    TransactionTemplate tx;

    /**
     * The old way: add up the refunds in Java, and insert if there is room. Between the check and the insert, the old
     * code also asked the payment provider whether the card could take a refund; 100 ms stands in for that call.
     */
    boolean oldRefund(long order, long paise) {
        return Boolean.TRUE.equals(tx.execute(status -> {
            long total = jdbc.sql("SELECT total_paise FROM orders WHERE id = ?").param(order).query(Long.class).single();
            long refunded = refundedOrPending(order);
            if (refunded + paise > total) {
                return false;
            }
            jdbc.sql("SELECT pg_sleep(0.1)").query().singleValue();
            jdbc.sql("INSERT INTO refunds (order_id, amount_paise, reason, status, needs_second_approval, requested_by, decided_by, decided_at) "
                    + "VALUES (?, ?, 'Damaged on delivery', 'APPROVED', false, 'asha', 'asha', now())").params(order, paise).update();
            return true;
        }));
    }

    @Test
    void theOldJavaCheckLetsConcurrentRefundsAddUpToMoreThanTheOrder() throws Exception {
        List<Boolean> results = atOnce(20, () -> oldRefund(MIXER, 100_000));
        assertThat(results.stream().filter(b -> b).count()).as("refunds accepted").isGreaterThan(4);
        assertThat(refundedOrPending(MIXER)).as("refunded, in paise, of a ₹4,999 order").isGreaterThan(499_900);
    }

    @Test
    void theApiAcceptsOnlyWhatFitsUnderTwentyAtOnce() throws Exception {
        List<Integer> statuses = atOnce(20, () -> refund(MIXER, 100_000, "asha").andReturn().getResponse().getStatus());
        assertThat(statuses).filteredOn(s -> s == 201).hasSize(4);
        assertThat(statuses).filteredOn(s -> s == 409).hasSize(16);
        assertThat(refundedOrPending(MIXER)).isEqualTo(400_000).isEqualTo(reserved(MIXER));
    }

    /** n virtual threads, released together. */
    static <T> List<T> atOnce(int n, java.util.concurrent.Callable<T> work) throws Exception {
        CountDownLatch start = new CountDownLatch(1);
        List<Future<T>> futures = new ArrayList<>();
        try (var pool = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < n; i++) {
                futures.add(pool.submit(() -> {
                    start.await();
                    return work.call();
                }));
            }
            start.countDown();
            List<T> out = new ArrayList<>();
            for (Future<T> f : futures) {
                out.add(f.get());
            }
            return out;
        }
    }
}
