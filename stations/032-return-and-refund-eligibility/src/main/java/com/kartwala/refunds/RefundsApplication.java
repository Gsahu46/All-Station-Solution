package com.kartwala.refunds;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.time.Clock;

@SpringBootApplication
public class RefundsApplication {

    public static void main(String[] args) {
        SpringApplication.run(RefundsApplication.class, args);
    }

    /** "Now" as a bean, so tests can fix it. */
    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
