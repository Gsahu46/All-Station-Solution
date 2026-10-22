package com.tijori.wallets;

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
 * Real parallel requests through the API. Writing a top-up takes 200 ms here (a trigger), so the requests overlap
 * every time. If the application's check lets an extra top-up through, the database's rule refuses it with a 500:
 * a bug in the application, which these tests then see.
 */
class TopUpConcurrencyTest extends ApiTest {

    @BeforeEach
    void slowTopUps() {
        jdbc.sql("""
                CREATE OR REPLACE FUNCTION slow_top_ups() RETURNS trigger AS $$ BEGIN PERFORM pg_sleep(0.2); RETURN NEW; END $$ LANGUAGE plpgsql;
                CREATE OR REPLACE TRIGGER a_slow_top_ups BEFORE INSERT ON top_ups FOR EACH ROW EXECUTE FUNCTION slow_top_ups()""").update();
    }

    @AfterEach
    void normalTopUps() {
        jdbc.sql("DROP TRIGGER a_slow_top_ups ON top_ups; DROP FUNCTION slow_top_ups()").update();
    }

    List<Integer> atOnce(long wallet, long paise, int times) throws Exception {
        CountDownLatch start = new CountDownLatch(1);
        List<Future<Integer>> futures = new ArrayList<>();
        try (ExecutorService threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < times; i++) {
                futures.add(threads.submit(() -> {
                    start.await();
                    try {
                        return topUp(wallet, paise).andReturn().getResponse().getStatus();
                    } catch (Exception e) {
                        return 500;   // the database's rule refused what the application let through
                    }
                }));
            }
            start.countDown();
        }
        List<Integer> statuses = new ArrayList<>();
        for (Future<Integer> f : futures) {
            statuses.add(f.get());
        }
        return statuses;
    }

    @Test
    void tenTopUpsOfFourThousandAtOnceLetTwoThrough() throws Exception {
        List<Integer> statuses = atOnce(ANANYA, 400000, 10);
        assertThat(statuses).filteredOn(s -> s == 201).hasSize(2);
        assertThat(statuses).filteredOn(s -> s == 409).hasSize(8);
        assertThat(toppedUp(ANANYA)).isEqualTo(800000);
        assertThat(balance(ANANYA)).isEqualTo(50000 + 800000);
    }

    @Test
    void twoWalletsDoNotWaitForEachOther() throws Exception {
        long started = System.nanoTime();
        try (ExecutorService threads = Executors.newVirtualThreadPerTaskExecutor()) {
            Future<Integer> a = threads.submit(() -> topUp(ANANYA, 100000).andReturn().getResponse().getStatus());
            Future<Integer> v = threads.submit(() -> topUp(VIKRAM, 100000).andReturn().getResponse().getStatus());
            assertThat(List.of(a.get(), v.get())).containsExactly(201, 201);
        }
        assertThat((System.nanoTime() - started) / 1_000_000).isLessThan(390);   // two 200 ms writes side by side, not one after the other
    }
}
