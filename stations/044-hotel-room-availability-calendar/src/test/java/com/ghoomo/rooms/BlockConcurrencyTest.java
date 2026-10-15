package com.ghoomo.rooms;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;

/** Several desks selling the same room at once: no night is ever held twice, and nobody gets a 500. */
class BlockConcurrencyTest extends ApiTest {

    @Test
    void twentyRequestsForTheSameNightsHoldItOnce() throws Exception {
        List<Integer> statuses = together(20, () -> hold(102, "2026-08-01", "2026-08-04").andReturn().getResponse().getStatus());
        assertThat(statuses).filteredOn(s -> s == 201).hasSize(1);
        assertThat(statuses).filteredOn(s -> s == 409).hasSize(19);
        assertThat(blocksOf(102)).isEqualTo(1);
    }

    @Test
    void staggeredOverlappingRequestsNeverShareANight() throws Exception {
        // 30 requests of 3 nights each, starting one day apart: neighbours overlap.
        AtomicInteger day = new AtomicInteger();
        List<Integer> statuses = together(30, () -> {
            int d = day.getAndIncrement();
            return hold(102, "2026-09-01".replace("01", "%02d".formatted(1 + d % 28)), "2026-09-01".replace("01", "%02d".formatted(4 + d % 28)))
                    .andReturn().getResponse().getStatus();
        });
        assertThat(statuses).doesNotContain(500).containsOnly(201, 409, 400);
        long sharedNights = jdbc.sql("""
                SELECT count(*) FROM room_blocks a JOIN room_blocks b
                  ON a.room_id = b.room_id AND a.id < b.id AND a.check_in < b.check_out AND a.check_out > b.check_in""").query(Long.class).single();
        assertThat(sharedNights).isZero();
    }
}
