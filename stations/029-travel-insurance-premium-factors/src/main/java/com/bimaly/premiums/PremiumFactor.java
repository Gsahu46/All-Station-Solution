package com.bimaly.premiums;

/**
 * One step of the premium: takes the running total (paise) and returns the new one, with a line for the breakdown.
 * Each factor is its own bean; the calculator receives all of them as a List, in @Order. Factors hold no per-quote
 * state: they are singletons shared by every request at once.
 */
interface PremiumFactor {

    record Step(String factor, String note, long totalPaise) {
    }

    Step apply(Trip trip, long totalPaise);
}
