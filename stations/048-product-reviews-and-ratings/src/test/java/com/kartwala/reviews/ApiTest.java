package com.kartwala.reviews;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * Shared setup: the app on a real PostgreSQL with the demo catalogue and no reviews. Headphones (product 1): Asha (1)
 * and Vikram (2) have them delivered, Neha (3) is waiting for delivery, Imran (4) never bought them.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;

    @BeforeEach
    void noReviews() {
        jdbc.sql("TRUNCATE reviews RESTART IDENTITY").update();
        jdbc.sql("DELETE FROM purchases WHERE id > 4").update();
        jdbc.sql("DELETE FROM customers WHERE id > 4").update();
        jdbc.sql("INSERT INTO product_ratings (product_id) SELECT id FROM products ON CONFLICT DO NOTHING").update();
        jdbc.sql("UPDATE product_ratings SET review_count = 0, star_total = 0").update();
    }

    ResultActions review(long product, long customer, int stars) throws Exception {
        return mvc.perform(post("/products/{id}/reviews", product).contentType(MediaType.APPLICATION_JSON)
                .content("{\"customerId\":%d,\"stars\":%d,\"text\":\"Good bass, the battery really lasts.\"}".formatted(customer, stars)));
    }

    /** Adds n customers (ids from 100) with a delivered purchase of the product (purchase ids from 100). */
    void deliveredBuyers(int n, long product) {
        jdbc.sql("INSERT INTO customers (id, name) SELECT 99 + g, 'Buyer ' || g FROM generate_series(1, ?) g").param(n).update();
        jdbc.sql("INSERT INTO purchases (id, customer_id, product_id, delivered_on) SELECT 99 + g, 99 + g, ?, DATE '2026-10-01' FROM generate_series(1, ?) g")
                .params(product, n).update();
    }

    /** Runs n copies of the task on virtual threads, all released together by one latch. */
    static <T> List<T> together(int n, Callable<T> task) throws Exception {
        CountDownLatch start = new CountDownLatch(1);
        List<Future<T>> futures = new ArrayList<>();
        try (ExecutorService threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < n; i++) {
                futures.add(threads.submit(() -> {
                    start.await();
                    return task.call();
                }));
            }
            start.countDown();
        }
        List<T> results = new ArrayList<>();
        for (Future<T> f : futures) {
            results.add(f.get());
        }
        return results;
    }
}
