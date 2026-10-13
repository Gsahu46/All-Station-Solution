package com.rydo.fares;

import java.math.BigDecimal;

/** An auto-meter style rule: the first includedKm are in the base fare; each km after costs perKmAfter. */
record MeterRule(BigDecimal base, BigDecimal includedKm, BigDecimal perKmAfter) implements FareRule {

    @Override
    public BigDecimal fare(BigDecimal km) {
        BigDecimal extraKm = km.subtract(includedKm).max(BigDecimal.ZERO);
        return base.add(perKmAfter.multiply(extraKm));
    }
}
