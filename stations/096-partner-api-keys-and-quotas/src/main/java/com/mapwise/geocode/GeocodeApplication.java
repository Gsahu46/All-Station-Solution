package com.mapwise.geocode;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;
import org.springframework.context.annotation.Bean;

import java.time.Clock;

@SpringBootApplication
@ConfigurationPropertiesScan
public class GeocodeApplication {

    public static void main(String[] args) {
        SpringApplication.run(GeocodeApplication.class, args);
    }

    /** Buckets refill by this clock, so tests can move time instead of sleeping. */
    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
