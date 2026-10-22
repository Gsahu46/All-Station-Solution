package com.dakroute.rates;

import org.springframework.stereotype.Component;

import java.util.Set;

/**
 * Demo rules, not Dakroute's real tariff. Zone by PIN code: the same first three digits is LOCAL, the same first two
 * REGIONAL, anything else NATIONAL. Price per started 500 g of chargeable weight; EXPRESS costs half as much again.
 * Chargeable weight is the larger of the actual weight and the volumetric weight (length x width x height in cm / 5,
 * in grams, the common 5000 divisor). GST 18%, rounded to the nearest paisa.
 */
@Component
class RateCard {

    enum Zone { LOCAL, REGIONAL, NATIONAL }

    enum Service { STANDARD, EXPRESS }

    static final int MAX_WEIGHT_GRAMS = 50_000;
    /** Demo rule: PIN codes this network does not serve yet. */
    static final Set<String> NOT_SERVED = Set.of("744101", "194101");

    static Zone zone(String from, String to) {
        return from.regionMatches(0, to, 0, 3) ? Zone.LOCAL : from.regionMatches(0, to, 0, 2) ? Zone.REGIONAL : Zone.NATIONAL;
    }

    static long volumetricGrams(int lengthCm, int widthCm, int heightCm) {
        return (long) lengthCm * widthCm * heightCm / 5;
    }

    static long pricePaise(Zone zone, Service service, long chargeableGrams) {
        long perSlab = switch (zone) {
            case LOCAL -> 4000;
            case REGIONAL -> 5500;
            case NATIONAL -> 7500;
        };
        long slabs = (chargeableGrams + 499) / 500;
        long price = perSlab * slabs;
        return service == Service.EXPRESS ? price * 3 / 2 : price;
    }

    static long gstPaise(long pricePaise) {
        return (pricePaise * 18 + 50) / 100;
    }

    static int days(Zone zone, Service service) {
        return switch (zone) {
            case LOCAL -> 1;
            case REGIONAL -> service == Service.EXPRESS ? 2 : 3;
            case NATIONAL -> service == Service.EXPRESS ? 3 : 5;
        };
    }
}
