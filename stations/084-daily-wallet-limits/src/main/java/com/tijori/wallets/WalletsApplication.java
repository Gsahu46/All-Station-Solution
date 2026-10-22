package com.tijori.wallets;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.time.Clock;

@SpringBootApplication
public class WalletsApplication {

    public static void main(String[] args) {
        SpringApplication.run(WalletsApplication.class, args);
    }

    /** Which day a top-up counts for comes from here, so tests can stand just before and after midnight in India. */
    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
