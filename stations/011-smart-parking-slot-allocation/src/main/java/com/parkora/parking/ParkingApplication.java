package com.parkora.parking;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.time.Clock;

@SpringBootApplication
public class ParkingApplication {

    public static void main(String[] args) {
        SpringApplication.run(ParkingApplication.class, args);
    }

    /** The garage asks this clock for "now", so tests can move time forward instead of waiting two hours. */
    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
