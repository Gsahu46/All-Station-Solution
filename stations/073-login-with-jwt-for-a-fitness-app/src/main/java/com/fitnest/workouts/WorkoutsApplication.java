package com.fitnest.workouts;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.time.Clock;

@SpringBootApplication
public class WorkoutsApplication {

    public static void main(String[] args) {
        SpringApplication.run(WorkoutsApplication.class, args);
    }

    /** Issuing and checking tokens both read the time from here, so tests can move it past an expiry. */
    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
