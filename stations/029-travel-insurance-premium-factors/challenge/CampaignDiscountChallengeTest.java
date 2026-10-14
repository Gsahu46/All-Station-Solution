package com.bimaly.premiums;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 2: a Diwali campaign takes 10% off, before the minimum is applied. The factor exists only when
 * bimaly.campaign.diwali=true (@ConditionalOnProperty), so switching the campaign off is a configuration change.
 */
class CampaignDiscountChallengeTest {

    final ApplicationContextRunner app = new ApplicationContextRunner()
            .withUserConfiguration(Rounding.Beans.class, Factors.Base.class, Factors.DestinationRisk.class, Factors.Age.class,
                    Factors.AdventureSports.class, Factors.Minimum.class, CampaignDiscount.class, PremiumCalculator.class);

    static final Trip SENIOR_IN_EUROPE = new Trip(67, Trip.Destination.EUROPE, 10, true);

    @Test
    void theDiscountAppliesOnlyWhenTheCampaignIsOn() {
        app.withPropertyValues("bimaly.campaign.diwali=true").run(ctx -> {
            PremiumCalculator.Quote q = ctx.getBean(PremiumCalculator.class).quote(SENIOR_IN_EUROPE);
            assertThat(q.breakdown()).extracting(PremiumFactor.Step::factor).contains("campaign");
            assertThat(q.premiumPaise()).isEqualTo(165_500);   // 183,875 less 10% = 165,487.5 -> 165,488, rounded up
        });
        app.run(ctx -> assertThat(ctx.getBean(PremiumCalculator.class).quote(SENIOR_IN_EUROPE).breakdown())
                .extracting(PremiumFactor.Step::factor).isEqualTo(List.of("base", "destination", "age", "adventure", "minimum")));
    }
}
