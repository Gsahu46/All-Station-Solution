package com.basketo.delivery;

import org.springframework.boot.autoconfigure.AutoConfigurations;
import org.springframework.boot.autoconfigure.context.ConfigurationPropertiesAutoConfiguration;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.boot.validation.autoconfigure.ValidationAutoConfiguration;
import org.springframework.context.annotation.Configuration;

/** A small context with just the settings, binding and validation: starts in milliseconds, or fails like the app would. */
final class ConfigRunner {

    @Configuration
    @EnableConfigurationProperties(DeliverySettings.class)
    static class SettingsOnly {
    }

    static final String[] PUNE = {"basketo.cities.pune.radius-km=6.0", "basketo.cities.pune.fee-paise=2500",
            "basketo.cities.pune.store.lat=18.5308", "basketo.cities.pune.store.lon=73.8475"};

    private ConfigRunner() {
    }

    static ApplicationContextRunner settings(String... more) {
        return new ApplicationContextRunner()
                .withConfiguration(AutoConfigurations.of(ConfigurationPropertiesAutoConfiguration.class, ValidationAutoConfiguration.class))
                .withUserConfiguration(SettingsOnly.class)
                .withPropertyValues(PUNE)
                .withPropertyValues(more);
    }
}
