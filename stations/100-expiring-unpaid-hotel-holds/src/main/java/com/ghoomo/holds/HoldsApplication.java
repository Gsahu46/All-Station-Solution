package com.ghoomo.holds;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.time.Clock;

@SpringBootApplication
public class HoldsApplication {

    public static void main(String[] args) {
        SpringApplication.run(HoldsApplication.class, args);
    }

    /** Every "now" comes from here, so tests can make holds expire without waiting 15 minutes. */
    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
