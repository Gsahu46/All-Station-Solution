package com.bimaly.premiums;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.core.annotation.Order;

import java.lang.reflect.Modifier;
import java.util.Arrays;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** How the beans are wired: the list's order, which rounding is which, scopes, and the startup check. */
@SpringBootTest
class FactorWiringTest {

    @Autowired
    List<PremiumFactor> factors;
    @Autowired
    @Qualifier("premium")
    Rounding premiumRounding;
    @Autowired
    Rounding defaultRounding;
    @Autowired
    ConfigurableApplicationContext context;

    @Test
    void theListComesInOrderOrder() {
        // a subsequence, not the exact list: a new factor may slot in between without breaking this test
        assertThat(factors).extracting(f -> f.getClass().getSimpleName())
                .containsSubsequence("Base", "DestinationRisk", "Age", "AdventureSports", "Minimum");
    }

    @Test
    void theQualifiedRoundingRoundsUpAndThePrimaryRoundsToNearest() {
        assertThat(premiumRounding.toRupee(106_301)).isEqualTo(106_400);
        assertThat(defaultRounding.toRupee(106_301)).isEqualTo(106_300);
    }

    @Test
    void factorsAreStatelessSingletons() {
        for (String name : context.getBeanNamesForType(PremiumFactor.class)) {
            assertThat(context.getBeanFactory().getBeanDefinition(name).isSingleton()).as(name).isTrue();
            Class<?> type = context.getBean(name).getClass();
            assertThat(Arrays.stream(type.getDeclaredFields()).filter(f -> !Modifier.isStatic(f.getModifiers())))
                    .as(type.getSimpleName() + " keeps no per-quote state").isEmpty();
        }
    }

    @Order(30)
    static class SecondAgeFactor implements PremiumFactor {
        public Step apply(Trip trip, long total) {
            return new Step("age again", "", total);
        }
    }

    @Test
    void twoFactorsWithTheSameOrderStopTheAppStarting() {
        new ApplicationContextRunner()
                .withUserConfiguration(Rounding.Beans.class, Factors.Base.class, Factors.Age.class, SecondAgeFactor.class, PremiumCalculator.class)
                .run(ctx -> assertThat(ctx).hasFailed().getFailure().rootCause()
                        .isInstanceOf(IllegalStateException.class).hasMessageContaining("shares @Order(30)"));
    }
}
