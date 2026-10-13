package com.tijori.loans;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;
import org.springframework.context.annotation.Bean;

import java.time.Clock;
import java.time.ZoneId;

@SpringBootApplication
@ConfigurationPropertiesScan
public class LoansApplication {

    public static void main(String[] args) {
        SpringApplication.run(LoansApplication.class, args);
    }

    /** "Today" for picking the rate, in India's time zone: a quote at 00:30 IST on 1 Oct uses the 1 Oct rate. */
    @Bean
    Clock clock() {
        return Clock.system(ZoneId.of("Asia/Kolkata"));
    }
}
