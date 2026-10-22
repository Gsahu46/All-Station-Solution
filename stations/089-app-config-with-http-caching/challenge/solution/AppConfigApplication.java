package com.streamo.config;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.time.Clock;

@SpringBootApplication
public class AppConfigApplication {

    public static void main(String[] args) {
        SpringApplication.run(AppConfigApplication.class, args);
    }

    /** Publish times come from here, so tests can publish at a known second. */
    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
