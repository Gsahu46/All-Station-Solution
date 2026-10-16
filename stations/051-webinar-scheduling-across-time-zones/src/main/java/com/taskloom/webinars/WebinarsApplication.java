package com.taskloom.webinars;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.time.Clock;

@SpringBootApplication
public class WebinarsApplication {

    public static void main(String[] args) {
        SpringApplication.run(WebinarsApplication.class, args);
    }

    /** "Now" comes from here, never from Instant.now(), so tests can fix it. */
    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
