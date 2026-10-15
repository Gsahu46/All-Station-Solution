package com.mediqo.reminders;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.time.Clock;

@SpringBootApplication
public class RemindersApplication {

    public static void main(String[] args) {
        SpringApplication.run(RemindersApplication.class, args);
    }

    /** "Now" as a bean, so tests can set it. */
    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
