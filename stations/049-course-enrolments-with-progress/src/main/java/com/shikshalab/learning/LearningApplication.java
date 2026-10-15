package com.shikshalab.learning;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.time.Clock;
import java.time.ZoneId;

@SpringBootApplication
public class LearningApplication {

    public static void main(String[] args) {
        SpringApplication.run(LearningApplication.class, args);
    }

    /** Dates are Indian dates: an enrolment at 00:30 IST is dated that day, not the previous UTC day. */
    @Bean
    Clock clock() {
        return Clock.system(ZoneId.of("Asia/Kolkata"));
    }
}
