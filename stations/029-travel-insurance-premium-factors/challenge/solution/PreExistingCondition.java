package com.bimaly.premiums;

import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

/** Challenge 1: +40% on the cover cost, after age and before the flat adventure add-on. A new bean; nothing else changes. */
@Component
@Order(35)
class PreExistingCondition implements PremiumFactor {

    public Step apply(Trip trip, long total) {
        return trip.preExistingCondition() ? new Step("pre-existing condition", "x 1.40", Factors.times(total, "1.40"))
                : new Step("pre-existing condition", "none declared", total);
    }
}
