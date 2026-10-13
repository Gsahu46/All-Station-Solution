package com.rydo.fares;

import java.math.BigDecimal;

/** A flat base plus a price per km, never below a minimum. Used by bikes and cabs. */
record PerKmRule(BigDecimal base, BigDecimal perKm, BigDecimal minimum) implements FareRule {

    @Override
    public BigDecimal fare(BigDecimal km) {
        return base.add(perKm.multiply(km)).max(minimum);
    }
}
