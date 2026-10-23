package com.chaupal.previews;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.net.InetAddress;

@SpringBootApplication
public class PreviewsApplication {

    public static void main(String[] args) {
        SpringApplication.run(PreviewsApplication.class, args);
    }

    /** Real DNS. */
    @Bean
    NameLookup nameLookup() {
        return InetAddress::getAllByName;
    }
}
