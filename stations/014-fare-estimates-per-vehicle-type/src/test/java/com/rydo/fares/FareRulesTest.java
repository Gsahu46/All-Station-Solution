package com.rydo.fares;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;

/** Each fare rule at its boundaries, and the rounding to whole rupees. */
class FareRulesTest {

    static long fare(VehicleType v, String km) {
        return v.farePaise(new BigDecimal(km));
    }

    @Test
    void theAutoMeterIncludesTheFirstTwoKm() {
        assertThat(fare(VehicleType.AUTO, "0")).isEqualTo(3000);
        assertThat(fare(VehicleType.AUTO, "2.0")).isEqualTo(3000);
        assertThat(fare(VehicleType.AUTO, "2.1")).isEqualTo(3200);   // 31.50 rounds half up to 32
        assertThat(fare(VehicleType.AUTO, "3.0")).isEqualTo(4500);
    }

    @Test
    void minimumsApplyToShortRides() {
        assertThat(fare(VehicleType.BIKE, "1.0")).isEqualTo(3000);   // 26 is below the 30 minimum
        assertThat(fare(VehicleType.BIKE, "1.7")).isEqualTo(3000);   // 30.20 -> 30
        assertThat(fare(VehicleType.CAB, "2.0")).isEqualTo(8000);    // 78 is below the 80 minimum
        assertThat(fare(VehicleType.CAB, "2.2")).isEqualTo(8100);    // 80.80 -> 81
    }

    @Test
    void halfARupeeRoundsUp() {
        assertThat(fare(VehicleType.BIKE, "6.25")).isEqualTo(5800);  // 57.50 -> 58
        assertThat(fare(VehicleType.CAB, "6.4")).isEqualTo(14000);   // 139.60 -> 140
    }

    @Test
    void theServerDistanceIsRoundedToATenthOfAKm() {
        assertThat(Location.roadKm(new Location(12.9756, 77.6066), new Location(12.9352, 77.6245))).isEqualByComparingTo("6.4");
        assertThat(Location.roadKm(new Location(12.9756, 77.6066), new Location(12.9756, 77.6066))).isEqualByComparingTo("0.0");
    }
}
