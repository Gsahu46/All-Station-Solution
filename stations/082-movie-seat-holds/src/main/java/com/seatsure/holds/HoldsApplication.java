package com.seatsure.holds;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.time.Clock;

@SpringBootApplication
public class HoldsApplication {

    public static void main(String[] args) {
        SpringApplication.run(HoldsApplication.class, args);
    }

    /** Holds and their expiry read the time from here, so tests can move it past a hold's end. */
    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
