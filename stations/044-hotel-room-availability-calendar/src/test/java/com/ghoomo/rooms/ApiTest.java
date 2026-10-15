package com.ghoomo.rooms;

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

/** Shared setup: the app on a real PostgreSQL. Before each test, room 101 holds 10-12 June (Asha) and 15-16 June (Ravi). */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;
    @Autowired
    RoomBlockRepository blocks;

    @BeforeEach
    void demoBlocks() {
        jdbc.sql("TRUNCATE room_blocks RESTART IDENTITY").update();
        jdbc.sql("""
                INSERT INTO room_blocks (room_id, check_in, check_out, guest_name) VALUES
                    (101, DATE '2026-06-10', DATE '2026-06-12', 'Asha Verma'),
                    (101, DATE '2026-06-15', DATE '2026-06-16', 'Ravi Iyer')""").update();
    }

    ResultActions hold(long room, String checkIn, String checkOut) throws Exception {
        return mvc.perform(post("/rooms/{id}/blocks", room).contentType(MediaType.APPLICATION_JSON)
                .content("{\"checkIn\":\"%s\",\"checkOut\":\"%s\",\"guestName\":\"Test Guest\"}".formatted(checkIn, checkOut)));
    }

    long blocksOf(long room) {
        return jdbc.sql("SELECT count(*) FROM room_blocks WHERE room_id = ?").param(room).query(Long.class).single();
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
