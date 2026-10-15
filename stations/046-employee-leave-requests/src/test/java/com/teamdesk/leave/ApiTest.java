package com.teamdesk.leave;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import tools.jackson.databind.json.JsonMapper;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * Shared setup: the app on a real PostgreSQL, with no test transaction around it (exactly like production). Before
 * each test: no requests, Asha Verma (1) has 12 days, Rohan Iyer (2) has 2. Fri 6 to Tue 10 Nov 2026 is 3 working days.
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
    JsonMapper json;
    @Autowired
    LeaveRequestRepository requests;

    @BeforeEach
    void demoTeam() {
        jdbc.sql("TRUNCATE leave_requests RESTART IDENTITY").update();
        jdbc.sql("UPDATE employees SET balance_days = CASE id WHEN 1 THEN 12 WHEN 2 THEN 2 END").update();
    }

    ResultActions ask(long employee, String start, String end) throws Exception {
        return mvc.perform(post("/leave-requests").contentType(MediaType.APPLICATION_JSON)
                .content("{\"employeeId\":%d,\"startDate\":\"%s\",\"endDate\":\"%s\",\"reason\":\"Sister's wedding in Jaipur\"}".formatted(employee, start, end)));
    }

    long newRequest(long employee, String start, String end) throws Exception {
        return json.readTree(ask(employee, start, end).andReturn().getResponse().getContentAsString()).get("id").asLong();
    }

    ResultActions approve(long id) throws Exception {
        return mvc.perform(post("/leave-requests/{id}/approval", id));
    }

    int balanceInTheDatabase(long employee) {
        return jdbc.sql("SELECT balance_days FROM employees WHERE id = ?").param(employee).query(Integer.class).single();
    }

    String statusInTheDatabase(long request) {
        return jdbc.sql("SELECT status FROM leave_requests WHERE id = ?").param(request).query(String.class).single();
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
