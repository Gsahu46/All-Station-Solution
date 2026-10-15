package com.basketo.delivery;

import org.junit.jupiter.api.Test;
import org.springframework.boot.autoconfigure.AutoConfigurations;
import org.springframework.boot.autoconfigure.context.ConfigurationPropertiesAutoConfiguration;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.context.annotation.Configuration;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/** The first test written for this station: it reproduces the bugs before the fix. */
class UnvalidatedConfigTrapTest {

    /** The "before" settings: primitives, no validation, unknown keys ignored. Kept only in tests. */
    @ConfigurationProperties("basketo")
    record OldSettings(Map<String, OldCity> cities) {
        record OldCity(double radiusKm, long feePaise, long minimumOrderPaise) {
        }
    }

    @Configuration
    @EnableConfigurationProperties(OldSettings.class)
    static class OldApp {
    }

    /** The "before" check: the client said how far it was. Kept only in tests. */
    static boolean oldDeliverable(double clientDistanceKm, double radiusKm) {
        return clientDistanceKm <= radiusKm;
    }

    @Test
    void theOldSettingsStartWithAMisspeltKeyAndAMinimumOfZero() {
        new ApplicationContextRunner()
                .withConfiguration(AutoConfigurations.of(ConfigurationPropertiesAutoConfiguration.class))
                .withUserConfiguration(OldApp.class)
                .withPropertyValues("basketo.cities.pune.radius-km=6.0", "basketo.cities.pune.fee-paise=2500",
                        "basketo.cities.pune.minimun-order-paise=14900")   // "minimun": one letter wrong
                .run(context -> {
                    assertThat(context).hasNotFailed();
                    assertThat(context.getBean(OldSettings.class).cities().get("pune").minimumOrderPaise()).isZero();
                });
    }

    @Test
    void theRealSettingsRefuseToStartWithThatTypo() {
        ConfigRunner.settings("basketo.cities.pune.minimun-order-paise=14900")
                // the real key is now missing: a Long, not a long, so it is null, and @NotNull stops the start
                .run(context -> assertThat(context).hasFailed().getFailure()
                        .hasStackTraceContaining("cities[pune].minimumOrderPaise").hasStackTraceContaining("rejected value [null]"));
    }

    @Test
    void theOldCheckBelievesWhateverDistanceTheClientSends() {
        assertThat(oldDeliverable(0.0, 6.0)).isTrue();   // an address 13 km away, "0 km" according to the app
    }
}
