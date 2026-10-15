package com.kartwala.flashsale;

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
 * Shared setup: the app on a real PostgreSQL, no purchases, the demo sales restocked, and sale 10, an open sale whose
 * stock each test chooses. Demo sales: 1 open (500), 2 sold out, 3 ended, 4 not started.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;
    @Autowired
    FlashSaleStore store;

    @BeforeEach
    void freshSales() {
        jdbc.sql("TRUNCATE purchases").update();
        jdbc.sql("DELETE FROM flash_sales WHERE id = 10").update();
        jdbc.sql("UPDATE flash_sales SET stock_left = stock_total WHERE id <> 2").update();
    }

    void openSale(int stock) {
        jdbc.sql("""
                INSERT INTO flash_sales (id, product, stock_total, stock_left, price_paise, starts_at, ends_at)
                VALUES (10, 'Test phone', ?, ?, 999900, now() - interval '1 hour', now() + interval '1 hour')""").params(stock, stock).update();
    }

    ResultActions buy(long saleId, String customerId) throws Exception {
        return mvc.perform(post("/flash-sales/{id}/purchases", saleId).contentType(MediaType.APPLICATION_JSON)
                .content("{\"customerId\":\"" + customerId + "\"}"));
    }

    static String customer(int n) {
        return "C-%06d".formatted(n);
    }

    long purchases(long saleId) {
        return jdbc.sql("SELECT count(*) FROM purchases WHERE sale_id = ?").param(saleId).query(Long.class).single();
    }

    int stockLeft(long saleId) {
        return jdbc.sql("SELECT stock_left FROM flash_sales WHERE id = ?").param(saleId).query(Integer.class).single();
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
