package com.rydo.fares;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The first test written for this station: it reproduces the bug before the fix.
 * The "before" fare code is one method with an if-else chain. CAB_XL was added last.
 */
class IfElseChainTrapTest {

    /** Kept only in tests. The defaults at the top were the auto's numbers; whatever no branch catches is priced as an auto. */
    static double oldFare(String type, double km) {
        double base = 30, perKm = 20, freeKm = 2;   // perKm was 15; raised to 20 "for CAB_XL", which uses the defaults
        if (type.equals("BIKE")) {
            base = 20; perKm = 6; freeKm = 0;
        } else if (type.equals("CAB")) {
            base = 50; perKm = 14; freeKm = 0;
        } else if (type.equals("CAB_XL")) {
            base = 80; freeKm = 0;                   // perKm comes from the default above
        }
        return base + perKm * Math.max(0, km - freeKm);
    }

    @Test
    void addingCabXlChangedTheAutoFareThatNobodyTouched() {
        assertThat(oldFare("AUTO", 10)).isEqualTo(190.0);  // the auto meter says 30 + 8 x 15 = 150
        assertThat(oldFare("CAB_XL", 10)).isEqualTo(280.0);
    }

    @Test
    void withARulePerVehicleTypeEachFareStaysItsOwn() {
        assertThat(VehicleType.AUTO.farePaise(new BigDecimal("10"))).isEqualTo(150_00);
        assertThat(VehicleType.CAB_XL.farePaise(new BigDecimal("10"))).isEqualTo(280_00);
    }

    @Test
    void doubleArithmeticIsNotExactForMoney() {
        assertThat(0.1 + 0.2).isNotEqualTo(0.3);                                          // 0.30000000000000004
        assertThat(new BigDecimal("0.1").add(new BigDecimal("0.2"))).isEqualByComparingTo("0.3");
    }
}
