package com.bimaly.premiums;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.NoUniqueBeanDefinitionException;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** The first test written for this station: it reproduces both ways the old wiring went wrong. */
class FactorOrderTrapTest {

    static final Trip SENIOR_IN_EUROPE = new Trip(67, Trip.Destination.EUROPE, 10, true);

    /** The "before" quote service: one factor, injected by type. Kept only in tests. */
    record OldQuoteService(PremiumFactor factor) {
        long quote(Trip trip) {
            return factor.apply(trip, 0).totalPaise();
        }
    }

    @Configuration
    static class TwoFactorsOneConsumer {
        @Bean
        PremiumFactor base() {
            return new Factors.Base();
        }

        @Bean
        PremiumFactor age() {
            return new Factors.Age();
        }

        @Bean
        OldQuoteService oldQuoteService(PremiumFactor factor) {
            return new OldQuoteService(factor);
        }
    }

    @Configuration
    static class SomeoneAddedPrimary {
        @Bean
        PremiumFactor base() {
            return new Factors.Base();
        }

        @Bean
        @Primary
        PremiumFactor age() {
            return new Factors.Age();
        }

        @Bean
        OldQuoteService oldQuoteService(PremiumFactor factor) {
            return new OldQuoteService(factor);
        }
    }

    static long applyInOrder(List<PremiumFactor> factors, Trip trip) {
        long total = 0;
        for (PremiumFactor f : factors) {
            total = f.apply(trip, total).totalPaise();
        }
        return total;
    }

    @Test
    void oneInjectedFactorAmongSeveralStopsTheAppStarting() {
        new ApplicationContextRunner().withUserConfiguration(TwoFactorsOneConsumer.class)
                .run(context -> assertThat(context).hasFailed().getFailure().rootCause().isInstanceOf(NoUniqueBeanDefinitionException.class));
    }

    @Test
    void theQuickFixWithPrimaryStartsAndQuotesWithOneFactorOnly() {
        new ApplicationContextRunner().withUserConfiguration(SomeoneAddedPrimary.class).run(context -> {
            assertThat(context).hasNotFailed();
            assertThat(context.getBean(OldQuoteService.class).quote(SENIOR_IN_EUROPE)).isZero();   // age x nothing: a free policy
        });
    }

    @Test
    void theOrderOfTheFactorsChangesThePrice() {
        List<PremiumFactor> right = List.of(new Factors.Base(), new Factors.DestinationRisk(), new Factors.Age(), new Factors.AdventureSports(), new Factors.Minimum());
        List<PremiumFactor> scanned = List.of(new Factors.Base(), new Factors.DestinationRisk(), new Factors.AdventureSports(), new Factors.Age(), new Factors.Minimum());
        assertThat(applyInOrder(right, SENIOR_IN_EUROPE)).isEqualTo(183_875);
        assertThat(applyInOrder(scanned, SENIOR_IN_EUROPE)).isEqualTo(223_875);   // the adventure loading multiplied by age: Rs 400 more
    }
}
