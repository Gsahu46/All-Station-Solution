package com.paysetu.payments;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Two refunds of ₹600 on a ₹1,000 payment at the same moment. Reserving a refund takes 200 ms here (a trigger), so
 * both requests read the payment before either reserves. The row lock makes the second wait and see the first.
 */
class RefundConcurrencyTest extends ApiTest {

    @BeforeEach
    void slowReservations() {
        jdbc.sql("""
                CREATE OR REPLACE FUNCTION slow_reservations() RETURNS trigger AS $$ BEGIN PERFORM pg_sleep(0.2); RETURN NEW; END $$ LANGUAGE plpgsql;
                CREATE OR REPLACE TRIGGER slow_reservations BEFORE UPDATE OF refunded_paise ON payments FOR EACH ROW EXECUTE FUNCTION slow_reservations()""").update();
    }

    @AfterEach
    void normalReservations() {
        jdbc.sql("DROP TRIGGER slow_reservations ON payments; DROP FUNCTION slow_reservations()").update();
    }

    @Test
    void twoRefundsAtOnceCannotBothFit() throws Exception {
        pay("ORD-6001", 100000);
        CountDownLatch start = new CountDownLatch(1);
        List<Future<Integer>> futures = new ArrayList<>();
        try (ExecutorService threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 2; i++) {
                futures.add(threads.submit(() -> {
                    start.await();
                    try {
                        return refund(1, 60000).andReturn().getResponse().getStatus();
                    } catch (Exception e) {
                        return 500;   // the database's CHECK refused what the application let through
                    }
                }));
            }
            start.countDown();
        }
        List<Integer> statuses = new ArrayList<>();
        for (Future<Integer> f : futures) {
            statuses.add(f.get());
        }
        assertThat(statuses).containsExactlyInAnyOrder(201, 409);
        assertThat(alpha.refunds).containsExactly("ch_1 600.00");
    }
}
