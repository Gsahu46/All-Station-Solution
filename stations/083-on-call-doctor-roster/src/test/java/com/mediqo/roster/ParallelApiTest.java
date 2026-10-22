package com.mediqo.roster;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

/**
 * Real parallel requests through the API. Writing a roster change takes 200 ms here (a trigger), so the
 * transactions overlap every time: each reads the count before the other writes.
 */
abstract class ParallelApiTest extends ApiTest {

    @BeforeEach
    void slowChanges() {
        jdbc.sql("""
                CREATE OR REPLACE FUNCTION slow_changes() RETURNS trigger AS $$ BEGIN PERFORM pg_sleep(0.2); RETURN NEW; END $$ LANGUAGE plpgsql;
                CREATE OR REPLACE TRIGGER slow_changes BEFORE INSERT ON roster_changes FOR EACH ROW EXECUTE FUNCTION slow_changes()""").update();
    }

    @AfterEach
    void normalChanges() {
        jdbc.sql("DROP TRIGGER slow_changes ON roster_changes; DROP FUNCTION slow_changes()").update();
    }

    List<Integer> atOnce(String ward, String... doctors) throws Exception {
        CountDownLatch start = new CountDownLatch(1);
        List<Future<Integer>> futures = new ArrayList<>();
        try (ExecutorService threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (String doctor : doctors) {
                futures.add(threads.submit(() -> {
                    start.await();
                    return offCall(ward, doctor).andReturn().getResponse().getStatus();
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
}
