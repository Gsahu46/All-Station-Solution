package com.mediqo.reports;

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.testcontainers.rabbitmq.RabbitMQContainer;

/** A real RabbitMQ 4.1 in Docker, with its management API (the tests use it to cut workers off). */
@TestConfiguration(proxyBeanMethods = false)
class RabbitTestConfig {

    @Bean
    @ServiceConnection
    RabbitMQContainer rabbit() {
        return new RabbitMQContainer("rabbitmq:4.1-management-alpine");
    }
}
