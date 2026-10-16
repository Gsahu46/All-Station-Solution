package com.kartwala.catalog;

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.testcontainers.mongodb.MongoDBContainer;

/** A real MongoDB 8.0 in Docker, as a one-node replica set, so multi-document transactions are available. */
@TestConfiguration(proxyBeanMethods = false)
class MongoTestConfig {

    @Bean
    @ServiceConnection
    MongoDBContainer mongoContainer() {   // not "mongo": Spring Boot already names its MongoClient bean that
        return new MongoDBContainer("mongo:8.0").withReplicaSet();   // Testcontainers 2.0 no longer starts one by default
    }
}
