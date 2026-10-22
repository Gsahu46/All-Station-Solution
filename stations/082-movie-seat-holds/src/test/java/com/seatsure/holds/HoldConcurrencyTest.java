package com.seatsure.holds;

import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Real parallel requests against the real database: one seat, one holder; many pickers, no seat twice. */
class HoldConcurrencyTest extends ApiTest {

    /**
     * Each hold takes 200 ms to write, as on a busy database: the window in which two requests could both see a seat
     * free is wide open, so a missing lock shows up every time instead of by luck.
     */
    @org.junit.jupiter.api.BeforeEach
    void slowHolds() {
        jdbc.sql("""
                CREATE OR REPLACE FUNCTION slow_holds() RETURNS trigger AS $$ BEGIN PERFORM pg_sleep(0.2); RETURN NEW; END $$ LANGUAGE plpgsql;
                CREATE OR REPLACE TRIGGER slow_holds BEFORE INSERT ON holds FOR EACH ROW EXECUTE FUNCTION slow_holds()""").update();
    }

    @org.junit.jupiter.api.AfterEach
    void normalHolds() {
        jdbc.sql("DROP TRIGGER slow_holds ON holds; DROP FUNCTION slow_holds()").update();
    }

    <T> List<T> atOnce(int n, java.util.concurrent.Callable<T> work) throws Exception {
        CountDownLatch start = new CountDownLatch(1);
        List<Future<T>> futures = new ArrayList<>();
        try (ExecutorService threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < n; i++) {
                futures.add(threads.submit(() -> {
                    start.await();
                    return work.call();
                }));
            }
            start.countDown();
        }
        List<T> results = new ArrayList<>();
        for (Future<T> f : futures) {
            results.add(f.get());
        }
        return results;
    }

    @Test
    void tenPeopleHoldingF12AtOnceGetOneHold() throws Exception {
        List<Integer> statuses = atOnce(10, () -> hold("someone", "F12").andReturn().getResponse().getStatus());
        assertThat(statuses).filteredOn(s -> s == 201).hasSize(1);
        assertThat(statuses).isSubsetOf(201, 409, 503);   // the others: taken, or (rarely) busy for longer than the lock timeout
        assertThat(jdbc.sql("SELECT count(*) FROM holds").query(Long.class).single()).isEqualTo(1);
    }

    @Test
    void sevenPeopleAskingForAnyTwoGetFourteenDifferentSeats() throws Exception {
        List<String> bodies = atOnce(7, () -> holdRequest("{\"customer\":\"someone\",\"count\":2}").andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString());
        Set<String> seats = new HashSet<>();
        for (String b : bodies) {
            JSON.readTree(b).get("seatNos").forEach(s -> seats.add(s.asString()));
        }
        assertThat(seats).hasSize(14);   // SKIP LOCKED: nobody waited for, or got, a seat another picker was locking
    }

    @Test
    void aHoldThatRunsOutWhilePayingIsRefunded() throws Exception {
        String meera = holdId("meera", "F12");
        payments.delay = Duration.ofSeconds(1);
        CompletableFuture<String> paying = CompletableFuture.supplyAsync(() -> {
            try {
                return confirm(meera).andReturn().getResponse().getContentAsString();
            } catch (Exception e) {
                throw new IllegalStateException(e);
            }
        });
        Thread.sleep(300);
        later(Duration.ofMinutes(11));                       // the hold ends while the provider is still answering
        hold("arjun", "F12").andExpect(status().isCreated()); // and arjun holds the seat
        assertThat(JSON.readTree(paying.join()).get("detail").asString()).isEqualTo("The hold ran out while paying; the payment was refunded");
        assertThat(payments.refunds).containsKey(meera);
        assertThat(jdbc.sql("SELECT status FROM holds WHERE id = ?::uuid").param(meera).query(String.class).single()).isEqualTo("refunded");
        assertThat(jdbc.sql("SELECT booked_by FROM seats WHERE seat_no = 'F12'").query(String.class).list()).containsOnlyNulls();
    }
}
