package com.basketo.inventory;

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.testcontainers.mysql.MySQLContainer;

/** A real MySQL 8.4 in Docker (InnoDB, REPEATABLE READ by default), started once and shared by every test class. */
@TestConfiguration(proxyBeanMethods = false)
class MySqlTestConfig {

    @Bean
    @ServiceConnection
    MySQLContainer mysql() {
        return new MySQLContainer("mysql:8.4");
    }
}
