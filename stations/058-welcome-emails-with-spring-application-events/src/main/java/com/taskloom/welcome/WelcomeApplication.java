package com.taskloom.welcome;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

@SpringBootApplication
@EnableAsync   // @Async listeners run on Spring's task executor, not on the request's thread
public class WelcomeApplication {

    public static void main(String[] args) {
        SpringApplication.run(WelcomeApplication.class, args);
    }
}
