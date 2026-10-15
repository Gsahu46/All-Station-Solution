package com.teamdesk.leave;

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.testcontainers.postgresql.PostgreSQLContainer;

/** A real PostgreSQL 17 in Docker. Transactions, version checks and constraints must behave exactly as in production. */
@TestConfiguration(proxyBeanMethods = false)
class PostgresTestConfig {

    @Bean
    @ServiceConnection
    PostgreSQLContainer postgres() {
        return new PostgreSQLContainer("postgres:17-alpine");
    }
}
