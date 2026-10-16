package com.taskloom.signups;

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.testcontainers.mysql.MySQLContainer;
import org.testcontainers.postgresql.PostgreSQLContainer;

/**
 * One real PostgreSQL 17 and one real MySQL 8.4 in Docker, started once per test run and shared: by the Spring tests
 * (through @ServiceConnection) and by the trap test (through plain JDBC).
 */
final class Databases {

    static final PostgreSQLContainer POSTGRES = new PostgreSQLContainer("postgres:17-alpine");
    static final MySQLContainer MYSQL = new MySQLContainer("mysql:8.4");

    private Databases() {
    }

    @TestConfiguration(proxyBeanMethods = false)
    static class Postgres {
        @Bean
        @ServiceConnection
        PostgreSQLContainer postgres() {
            return POSTGRES;
        }
    }

    @TestConfiguration(proxyBeanMethods = false)
    static class MySql {
        @Bean
        @ServiceConnection
        MySQLContainer mysql() {
            return MYSQL;
        }
    }
}
