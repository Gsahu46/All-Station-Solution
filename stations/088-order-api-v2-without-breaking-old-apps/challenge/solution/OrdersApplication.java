package com.kartwala.orders;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.time.Clock;

@SpringBootApplication
public class OrdersApplication {

    public static void main(String[] args) {
        SpringApplication.run(OrdersApplication.class, args);
    }

    /** The sunset is checked against this clock, so tests can stand just before and after it. */
    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
