package com.hireloop.resets;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.time.Clock;

@SpringBootApplication
public class ResetsApplication {

    public static void main(String[] args) {
        SpringApplication.run(ResetsApplication.class, args);
    }

    /** "Now" comes from here, so tests can move time forward past an expiry. */
    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
