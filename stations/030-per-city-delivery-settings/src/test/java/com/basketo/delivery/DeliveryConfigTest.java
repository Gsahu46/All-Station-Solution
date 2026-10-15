package com.basketo.delivery;

import org.junit.jupiter.api.Test;
import org.springframework.boot.WebApplicationType;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.StandardEnvironment;
import org.springframework.core.env.SystemEnvironmentPropertySource;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

/** Configuration at work: validation at startup, environment variables, profiles, replaceable defaults, distance. */
class DeliveryConfigTest {

    @Test
    void invalidValuesStopTheAppStartingAndNameTheProperty() {
        ConfigRunner.settings("basketo.cities.pune.minimum-order-paise=0")
                .run(c -> assertThat(c).hasFailed().getFailure().hasStackTraceContaining("minimumOrderPaise"));
        ConfigRunner.settings("basketo.cities.pune.minimum-order-paise=14900", "basketo.cities.pune.radius-km=60")
                .run(c -> assertThat(c).hasFailed().getFailure().hasStackTraceContaining("radiusKm"));
        ConfigRunner.settings()   // minimum-order-paise missing altogether
                .run(c -> assertThat(c).hasFailed().getFailure().hasStackTraceContaining("minimumOrderPaise"));
        ConfigRunner.settings("basketo.cities.pune.minimum-order-paise=14900").run(c -> assertThat(c).hasNotFailed());
    }

    @Test
    void aMisspeltExtraKeyStopsTheAppStartingToo() {
        // every real key present, plus one nobody reads: ignoreUnknownFields = false refuses it
        ConfigRunner.settings("basketo.cities.pune.minimum-order-paise=14900", "basketo.cities.pune.feee-paise=1")
                .run(c -> assertThat(c).hasFailed().getFailure().hasStackTraceContaining("feee-paise"));
    }

    /** Starts the real app (no web server) with the given profile and pretend environment variables. */
    static ConfigurableApplicationContext app(String profile, Map<String, Object> environmentVariables) {
        StandardEnvironment env = new StandardEnvironment();
        env.getPropertySources().replace(StandardEnvironment.SYSTEM_ENVIRONMENT_PROPERTY_SOURCE_NAME,
                new SystemEnvironmentPropertySource(StandardEnvironment.SYSTEM_ENVIRONMENT_PROPERTY_SOURCE_NAME, environmentVariables));
        SpringApplicationBuilder builder = new SpringApplicationBuilder(DeliveryApplication.class).web(WebApplicationType.NONE).environment(env);
        return profile == null ? builder.run() : builder.profiles(profile).run();
    }

    @Test
    void anEnvironmentVariableOverridesOneValue() {
        try (var ctx = app(null, Map.of("BASKETO_CITIES_PUNE_FEEPAISE", "3000"))) {
            DeliverySettings s = ctx.getBean(DeliverySettings.class);
            assertThat(s.cities().get("pune").feePaise()).isEqualTo(3000);
            assertThat(s.cities().get("pune").minimumOrderPaise()).isEqualTo(14900);   // everything else from the file
        }
    }

    @Test
    void theDevProfileAddsATestCity() {
        try (var dev = app("dev", Map.of()); var normal = app(null, Map.of())) {
            assertThat(dev.getBean(DeliverySettings.class).cities()).containsKeys("testpur", "pune");
            assertThat(normal.getBean(DeliverySettings.class).cities()).doesNotContainKey("testpur");
        }
    }

    @Configuration
    static class RoadDistances {
        @Bean
        DistanceCalculator roadDistance() {
            return (from, lat, lon) -> 42.0;
        }
    }

    @Test
    void aBeanOfYourOwnReplacesTheDefaultCalculator() {
        try (var ctx = new SpringApplicationBuilder(DeliveryApplication.class, RoadDistances.class).web(WebApplicationType.NONE).run()) {
            assertThat(ctx.getBeansOfType(DistanceCalculator.class)).containsOnlyKeys("roadDistance");
        }
    }

    @Test
    void straightLineDistanceMatchesAKnownOne() {
        DistanceCalculator d = new DistanceAutoConfiguration().straightLine();
        assertThat(d.km(new DeliverySettings.Location(18.5204, 73.8567), 19.0760, 72.8777)).isCloseTo(120.15, within(0.01));   // Pune to Mumbai
    }
}
