package com.seatsure.sales;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

import java.net.http.HttpClient;
import java.time.Duration;

@SpringBootApplication
public class SalesApplication {

    public static void main(String[] args) {
        SpringApplication.run(SalesApplication.class, args);
    }

    /** The gateway's client, with both timeouts: a slow gateway costs one request thread for at most 3 s, and no connection. */
    @Bean
    RestClient payments(@Value("${seatsure.payments.url}") String url, @Value("${seatsure.payments.connect-timeout}") Duration connect,
                        @Value("${seatsure.payments.read-timeout}") Duration read) {
        JdkClientHttpRequestFactory factory = new JdkClientHttpRequestFactory(HttpClient.newBuilder().connectTimeout(connect).build());
        factory.setReadTimeout(read);
        return RestClient.builder().baseUrl(url).requestFactory(factory).build();
    }
}
