package com.paysetu.webhooks;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.time.Clock;

@SpringBootApplication
public class WebhooksApplication {

    public static void main(String[] args) {
        SpringApplication.run(WebhooksApplication.class, args);
    }

    /** Every "now" comes from here, so tests can move time on instead of waiting for retries. */
    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
