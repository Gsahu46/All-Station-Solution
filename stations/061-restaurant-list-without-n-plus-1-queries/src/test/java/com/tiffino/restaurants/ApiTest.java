package com.tiffino.restaurants;

import jakarta.persistence.EntityManagerFactory;
import org.hibernate.SessionFactory;
import org.hibernate.stat.Statistics;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;

import java.util.function.Supplier;

/**
 * Shared setup: the whole app on a real PostgreSQL with the demo data (3 Mumbai restaurants, 60 in Pune, none in
 * Nagpur). Hibernate statistics are switched on for tests only, to count the SQL statements each call sends.
 */
@SpringBootTest(properties = "spring.jpa.properties.hibernate.generate_statistics=true")
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;
    @Autowired
    EntityManagerFactory entityManagerFactory;

    record Counted<T>(T result, long queries) {
    }

    /** Runs the call and counts the JDBC statements Hibernate prepared for it. */
    <T> Counted<T> counting(Supplier<T> call) {
        Statistics statistics = entityManagerFactory.unwrap(SessionFactory.class).getStatistics();
        statistics.clear();
        T result = call.get();
        return new Counted<>(result, statistics.getPrepareStatementCount());
    }
}
