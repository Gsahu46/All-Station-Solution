package com.streamo.devices;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.time.Clock;

@SpringBootApplication
public class DevicesApplication {

    public static void main(String[] args) {
        SpringApplication.run(DevicesApplication.class, args);
    }

    /** Issuing and checking tokens both read the time from here, so tests can move it past an expiry. */
    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
