package com.parkora.parking;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;

/** The tariff on its own: every boundary of "every started hour". */
class FeeTest {

    @Test
    void everyStartedHourCounts() {
        assertThat(Fee.hoursCharged(Duration.ZERO)).isEqualTo(1);
        assertThat(Fee.hoursCharged(Duration.ofMinutes(1))).isEqualTo(1);
        assertThat(Fee.hoursCharged(Duration.ofMinutes(60))).isEqualTo(1);
        assertThat(Fee.hoursCharged(Duration.ofMinutes(60).plusSeconds(1))).isEqualTo(2);
        assertThat(Fee.hoursCharged(Duration.ofMinutes(120))).isEqualTo(2);
        assertThat(Fee.hoursCharged(Duration.ofMinutes(121))).isEqualTo(3);
    }

    @Test
    void feesInPaiseByVehicleType() {
        assertThat(Fee.feePaise(VehicleType.CAR, Duration.ofMinutes(45))).isEqualTo(4_000);
        assertThat(Fee.feePaise(VehicleType.CAR, Duration.ofHours(7))).isEqualTo(4_000 + 6 * 3_000);
        assertThat(Fee.feePaise(VehicleType.BIKE, Duration.ofMinutes(61))).isEqualTo(2_000 + 1_000);
    }

    @Test
    void integerDivisionWouldHaveRoundedDown() {
        // The usual slip: minutes / 60 is 1 for 119 minutes. ceilDiv gives the 2 hours the sign at the gate promises.
        assertThat(119 / 60).isEqualTo(1);
        assertThat(Fee.hoursCharged(Duration.ofMinutes(119))).isEqualTo(2);
    }
}
