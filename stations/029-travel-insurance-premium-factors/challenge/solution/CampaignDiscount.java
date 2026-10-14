package com.bimaly.premiums;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

/** Challenge 2: 10% off during the Diwali campaign, before the minimum. Exists only while the property is true. */
@Component
@Order(90)
@ConditionalOnProperty("bimaly.campaign.diwali")
class CampaignDiscount implements PremiumFactor {

    public Step apply(Trip trip, long total) {
        return new Step("campaign", "Diwali campaign, 10% off", Factors.times(total, "0.90"));
    }
}
