package com.seatsure.holds;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.time.Duration;
import java.util.concurrent.CompletableFuture;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 2: HoldSweeper.sweep(batchSize) marks expired holds 'expired' and clears their seats, a batch at a time.
 * Two app instances run it at once: with FOR UPDATE SKIP LOCKED they share the work, and no hold is swept twice.
 * Returns how many holds this call swept.
 */
class ExpiredHoldSweepChallengeTest extends ApiTest {

    @Autowired
    HoldSweeper sweeper;

    @Test
    void twoSweepersShareTheWork() throws Exception {
        for (String seat : new String[]{"E10", "E11", "E12", "E13", "E14", "G10"}) {
            hold("someone", seat);
        }
        later(Duration.ofMinutes(11));
        CompletableFuture<Integer> one = CompletableFuture.supplyAsync(() -> sweeper.sweep(10));
        CompletableFuture<Integer> two = CompletableFuture.supplyAsync(() -> sweeper.sweep(10));
        assertThat(one.join() + two.join()).isEqualTo(6);
        assertThat(jdbc.sql("SELECT count(*) FROM holds WHERE status = 'expired'").query(Long.class).single()).isEqualTo(6);
        assertThat(jdbc.sql("SELECT count(*) FROM seats WHERE hold_id IS NOT NULL").query(Long.class).single()).isZero();
        assertThat(sweeper.sweep(10)).isZero();
    }
}
