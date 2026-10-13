package com.rydo.fares;

import java.math.BigDecimal;

/**
 * The strategy: "given a distance, what does the ride cost, in rupees?" Each vehicle type holds one. The estimator
 * calls fare() without knowing which rule it is talking to, so a new vehicle type never touches existing code.
 */
interface FareRule {

    BigDecimal fare(BigDecimal km);
}
