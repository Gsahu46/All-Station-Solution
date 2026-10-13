package com.parkora.parking;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 2: a daily cap. Each full 24 hours costs at most the cap (car Rs 300, bike Rs 150); the hours after
 * the last full day are charged normally, but never more than one more cap.
 */
class DailyCapChallengeTest {

    @Test
    void aShortStayIsUnchanged() {
        assertThat(Fee.feePaise(VehicleType.CAR, Duration.ofHours(2))).isEqualTo(7_000);
    }

    @Test
    void aLongDayStopsAtTheCap() {
        assertThat(Fee.feePaise(VehicleType.CAR, Duration.ofHours(10))).isEqualTo(30_000); // 31,000 without the cap
        assertThat(Fee.feePaise(VehicleType.CAR, Duration.ofHours(24))).isEqualTo(30_000);
    }

    @Test
    void theNextDayStartsCountingAgain() {
        assertThat(Fee.feePaise(VehicleType.CAR, Duration.ofHours(25))).isEqualTo(30_000 + 4_000);
        assertThat(Fee.feePaise(VehicleType.BIKE, Duration.ofHours(30))).isEqualTo(15_000 + 2_000 + 5 * 1_000);
        assertThat(Fee.feePaise(VehicleType.CAR, Duration.ofHours(48))).isEqualTo(60_000);
    }
}
