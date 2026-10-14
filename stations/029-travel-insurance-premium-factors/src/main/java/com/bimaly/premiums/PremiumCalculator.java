package com.bimaly.premiums;

import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.core.annotation.AnnotationUtils;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Runs every factor in order. Spring injects all PremiumFactor beans as one List, sorted by @Order. A new factor is a
 * new @Component with an @Order: this class does not change.
 */
@Service
class PremiumCalculator {

    private static final Logger log = LoggerFactory.getLogger(PremiumCalculator.class);

    record Quote(long premiumPaise, long perDayPaise, List<PremiumFactor.Step> breakdown) {
    }

    private final List<PremiumFactor> factors;
    private final Rounding chargeRounding;
    private final Rounding displayRounding;

    PremiumCalculator(List<PremiumFactor> factors, @Qualifier("premium") Rounding chargeRounding, Rounding displayRounding) {
        this.factors = factors;
        this.chargeRounding = chargeRounding;
        this.displayRounding = displayRounding;   // no qualifier: the @Primary one
    }

    /**
     * Lifecycle callback: runs once, after injection, before the first quote. Refuses to start if a factor has no
     * @Order or shares one, because then the order, and so the price, would depend on how classes were scanned.
     */
    @PostConstruct
    void checkOrder() {
        Set<Integer> seen = new HashSet<>();
        for (PremiumFactor f : factors) {
            Order order = AnnotationUtils.findAnnotation(f.getClass(), Order.class);
            if (order == null || !seen.add(order.value())) {
                throw new IllegalStateException("Premium factor " + f.getClass().getSimpleName()
                        + (order == null ? " has no @Order" : " shares @Order(" + order.value() + ") with another factor"));
            }
        }
        log.info("Premium factors, in order: {}", factors.stream().map(f -> f.getClass().getSimpleName()).toList());
    }

    Quote quote(Trip trip) {
        long total = 0;
        List<PremiumFactor.Step> steps = new ArrayList<>();
        for (PremiumFactor f : factors) {
            PremiumFactor.Step step = f.apply(trip, total);
            steps.add(step);
            total = step.totalPaise();
        }
        long premium = chargeRounding.toRupee(total);
        return new Quote(premium, displayRounding.toRupee(premium / trip.days()), steps);
    }
}
