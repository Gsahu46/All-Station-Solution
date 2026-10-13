package com.rydo.fares;

import java.math.BigDecimal;
import java.math.RoundingMode;

/**
 * An enum with behaviour: each vehicle type carries its fare rule. Adding a type is one new line here; no other
 * type's line changes (open for extension, closed for modification). Every number is a demo rule, not a real tariff.
 */
public enum VehicleType {
    BIKE(new PerKmRule(rupees("20"), rupees("6"), rupees("30"))),
    AUTO(new MeterRule(rupees("30"), new BigDecimal("2"), rupees("15"))),
    CAB(new PerKmRule(rupees("50"), rupees("14"), rupees("80"))),
    CAB_XL(new PerKmRule(rupees("80"), rupees("20"), rupees("120")));

    private final FareRule rule;

    VehicleType(FareRule rule) {
        this.rule = rule;
    }

    /** The fare in whole paise, rounded to the nearest rupee (half up): riders see whole rupees. */
    long farePaise(BigDecimal km) {
        return rule.fare(km).setScale(0, RoundingMode.HALF_UP).movePointRight(2).longValueExact();
    }

    private static BigDecimal rupees(String amount) {
        return new BigDecimal(amount); // from a String: exact. new BigDecimal(0.1) would carry binary noise.
    }
}
