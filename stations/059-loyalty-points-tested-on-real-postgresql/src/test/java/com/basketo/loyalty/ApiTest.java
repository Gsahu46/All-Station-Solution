package com.basketo.loyalty;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicLong;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * Shared setup: the whole app (@SpringBootTest) on a real PostgreSQL 17 (@ServiceConnection in PostgresTestConfig).
 * Without Docker, every test here is SKIPPED with that reason, never failed and never passed.
 * Isolation: each test makes its own customers, so no test depends on another's data or on the order they run in.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
@Testcontainers(disabledWithoutDocker = true)
abstract class ApiTest {

    private static final AtomicLong NEXT_CUSTOMER = new AtomicLong(1000);

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;

    /** A customer no other test knows about, with no points yet. */
    long newCustomer() {
        long id = NEXT_CUSTOMER.incrementAndGet();
        jdbc.sql("INSERT INTO customers (id, name) VALUES (?, 'Test customer ' || ?)").params(id, id).update();
        return id;
    }

    ResultActions earn(long customer, String orderRef, long paise) throws Exception {
        return mvc.perform(post("/loyalty/{id}/earn", customer).contentType(MediaType.APPLICATION_JSON)
                .content("{\"orderRef\":\"%s\",\"amountPaise\":%d}".formatted(orderRef, paise)));
    }

    ResultActions redeem(long customer, int points) throws Exception {
        return mvc.perform(post("/loyalty/{id}/redeem", customer).contentType(MediaType.APPLICATION_JSON).content("{\"points\":" + points + "}"));
    }

    Integer balance(long customer) {
        return jdbc.sql("SELECT points FROM point_balances WHERE customer_id = ?").param(customer).query(Integer.class).optional().orElse(null);
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
