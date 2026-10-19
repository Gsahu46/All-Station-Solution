package com.streamo.devices;

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.testcontainers.postgresql.PostgreSQLContainer;

/** A real PostgreSQL 17 in Docker: the CHECK constraints on refresh tokens and devices behave exactly as in production. */
@TestConfiguration(proxyBeanMethods = false)
class PostgresTestConfig {

    @Bean
    @ServiceConnection
    PostgreSQLContainer postgres() {
        return new PostgreSQLContainer("postgres:17-alpine");
    }
}
