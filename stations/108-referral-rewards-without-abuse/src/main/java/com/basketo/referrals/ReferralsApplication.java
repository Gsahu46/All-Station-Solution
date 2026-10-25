package com.basketo.referrals;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class ReferralsApplication {

    public static void main(String[] args) {
        SpringApplication.run(ReferralsApplication.class, args);
    }
}
