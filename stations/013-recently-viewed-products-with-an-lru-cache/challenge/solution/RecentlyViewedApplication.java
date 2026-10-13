package com.kartwala.recent;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.time.Clock;

@SpringBootApplication
public class RecentlyViewedApplication {

    public static void main(String[] args) {
        SpringApplication.run(RecentlyViewedApplication.class, args);
    }

    /** Challenge 2: the store asks this clock for "now", so tests can move time. */
    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
