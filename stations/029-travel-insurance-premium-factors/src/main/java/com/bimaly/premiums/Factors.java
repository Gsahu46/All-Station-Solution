package com.bimaly.premiums;

import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Map;

/**
 * The premium factors (demo rates, not a real insurer's). Order is part of the rule: multipliers apply to the cover
 * cost, the adventure loading is a flat add-on that is not multiplied by age, and the minimum is checked last.
 */
final class Factors {

    private Factors() {
    }

    static long times(long paise, String multiplier) {
        return BigDecimal.valueOf(paise).multiply(new BigDecimal(multiplier)).setScale(0, RoundingMode.HALF_UP).longValueExact();
    }

    static String rupees(long paise) {
        return BigDecimal.valueOf(paise, 2).toPlainString();
    }

    @Component
    @Order(10)
    static class Base implements PremiumFactor {
        static final long PER_DAY_PAISE = 4_250;

        public Step apply(Trip trip, long total) {
            long base = PER_DAY_PAISE * trip.days();
            return new Step("base", trip.days() + " days at Rs " + rupees(PER_DAY_PAISE), base);
        }
    }

    @Component
    @Order(20)
    static class DestinationRisk implements PremiumFactor {
        static final Map<Trip.Destination, String> MULTIPLIER = Map.of(Trip.Destination.ASIA, "1.00", Trip.Destination.EUROPE, "1.75",
                Trip.Destination.USA_CANADA, "2.75", Trip.Destination.WORLDWIDE, "3.00");

        public Step apply(Trip trip, long total) {
            String m = MULTIPLIER.get(trip.destination());
            return new Step("destination", trip.destination() + " x " + m, times(total, m));
        }
    }

    @Component
    @Order(30)
    static class Age implements PremiumFactor {
        public Step apply(Trip trip, long total) {
            String m = trip.age() < 18 ? "0.80" : trip.age() <= 40 ? "1.00" : trip.age() <= 60 ? "1.30" : trip.age() <= 70 ? "1.80" : "2.50";
            return new Step("age", "age " + trip.age() + " x " + m, times(total, m));
        }
    }

    @Component
    @Order(40)
    static class AdventureSports implements PremiumFactor {
        static final long PER_DAY_PAISE = 5_000;

        public Step apply(Trip trip, long total) {
            if (!trip.adventureSports()) {
                return new Step("adventure", "no adventure sports", total);
            }
            return new Step("adventure", "adventure sports, Rs " + rupees(PER_DAY_PAISE) + " a day", total + PER_DAY_PAISE * trip.days());
        }
    }

    @Component
    @Order(100)
    static class Minimum implements PremiumFactor {
        static final long MINIMUM_PAISE = 19_900;

        public Step apply(Trip trip, long total) {
            return total >= MINIMUM_PAISE ? new Step("minimum", "above the Rs 199.00 minimum", total)
                    : new Step("minimum", "raised to the Rs 199.00 minimum", MINIMUM_PAISE);
        }
    }
}
