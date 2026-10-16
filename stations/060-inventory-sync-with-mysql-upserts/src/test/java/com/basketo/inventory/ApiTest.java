package com.basketo.inventory;

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
import java.util.stream.Collectors;
import java.util.stream.IntStream;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;

/** Shared setup: the whole app on a real MySQL 8.4. Before each test, no warehouse has any stock. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(MySqlTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;

    @BeforeEach
    void noStock() {
        jdbc.sql("DELETE FROM stock_levels").update();
    }

    ResultActions sync(long warehouse, String itemsJson) throws Exception {
        return mvc.perform(put("/warehouses/{id}/stock", warehouse).contentType(MediaType.APPLICATION_JSON).content("{\"items\":" + itemsJson + "}"));
    }

    /** n SKUs SKU-00001.. as a JSON array, all with the same quantity. */
    static String items(int n, int quantity) {
        return IntStream.rangeClosed(1, n).mapToObj(i -> "{\"sku\":\"SKU-%05d\",\"quantity\":%d}".formatted(i, quantity))
                .collect(Collectors.joining(",", "[", "]"));
    }

    Integer quantity(long warehouse, String sku) {
        return jdbc.sql("SELECT quantity FROM stock_levels WHERE warehouse_id = ? AND sku = ?").params(warehouse, sku)
                .query(Integer.class).optional().orElse(null);
    }

    long rows(long warehouse) {
        return jdbc.sql("SELECT count(*) FROM stock_levels WHERE warehouse_id = ?").param(warehouse).query(Long.class).single();
    }

    /** Runs n copies of the task on virtual threads, all released together by one latch; the task gets its index. */
    static <T> List<T> together(int n, IndexedTask<T> task) throws Exception {
        CountDownLatch start = new CountDownLatch(1);
        List<Future<T>> futures = new ArrayList<>();
        try (ExecutorService threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < n; i++) {
                int index = i;
                futures.add(threads.submit(() -> {
                    start.await();
                    return task.call(index);
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

    interface IndexedTask<T> {
        T call(int index) throws Exception;
    }
}
