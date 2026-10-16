package com.kartwala.prices;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.time.Clock;

@SpringBootApplication
public class PricesApplication {

    public static void main(String[] args) {
        SpringApplication.run(PricesApplication.class, args);
    }

    /** "Now" comes from here, so tests can fix it. */
    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
