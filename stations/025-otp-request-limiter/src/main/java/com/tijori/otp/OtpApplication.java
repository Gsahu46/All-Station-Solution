package com.tijori.otp;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.time.Clock;

@SpringBootApplication
public class OtpApplication {

    public static void main(String[] args) {
        SpringApplication.run(OtpApplication.class, args);
    }

    /** "Now" comes from here, so tests can move time forward instead of waiting 10 minutes. */
    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
