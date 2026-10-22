package com.paysetu.cards;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.time.Clock;

@SpringBootApplication
public class CardsApplication {

    public static void main(String[] args) {
        SpringApplication.run(CardsApplication.class, args);
    }

    /** Card expiry is checked against this clock, so tests can move past a card's last month. */
    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
